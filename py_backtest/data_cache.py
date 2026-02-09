"""
DataCache - 주가 데이터 캐시 모듈 (SRS NFR-301 준수)

역할: Yahoo Finance 데이터를 일일 1회만 수집하고, 이후 캐시에서 재사용
캐시 전략:
  1단계: 메모리 캐시 (가장 빠름)
  2단계: 디스크 캐시 - SQLite (서버 재시작 시에도 당일 데이터 유지)
  3단계: Yahoo Finance API 호출 (캐시 미스 시에만)

캐시 갱신 조건: fetchDate가 당일(00:00 이후)이면 캐시 사용, 아니면 재수집
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

# 디스크 캐시 DB 경로 (프로젝트 루트/data/cache.db)
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
_CACHE_DB_PATH = os.path.join(_CACHE_DIR, 'price_cache.db')


class DataCache:
    """
    주가 데이터 캐시 (메모리 + 디스크 2계층)

    LLD DataManager 캐싱 전략 구현:
      메모리 캐시 확인 → 디스크 캐시 확인 → Yahoo Finance API 호출
    """

    def __init__(self, cache_db_path: Optional[str] = None):
        """
        @param cache_db_path: 디스크 캐시 SQLite DB 경로 (기본값: data/price_cache.db)
        """
        self.cache_db_path = cache_db_path or _CACHE_DB_PATH

        # 1계층: 메모리 캐시 { stock_code: { fetchDate, data(DataFrame) } }
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

        # 디스크 캐시 DB 초기화
        self._init_disk_cache()

        logger.info(f"DataCache initialized (disk: {self.cache_db_path})")

    # ──────────────────────────────────────────────
    # 디스크 캐시 DB 초기화
    # ──────────────────────────────────────────────

    def _init_disk_cache(self):
        """디스크 캐시용 SQLite 테이블 생성"""
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)

        conn = sqlite3.connect(self.cache_db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    stock_code  TEXT    NOT NULL,
                    fetch_date  TEXT    NOT NULL,   -- 'YYYY-MM-DD'
                    data_json   TEXT    NOT NULL,   -- OHLCV JSON
                    created_at  TEXT    DEFAULT (datetime('now')),
                    PRIMARY KEY (stock_code, fetch_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ticker_cache (
                    stock_code  TEXT    PRIMARY KEY,
                    ticker      TEXT    NOT NULL,
                    fetch_date  TEXT    NOT NULL,
                    created_at  TEXT    DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
            logger.info("Disk cache DB initialized")
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────

    def get(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        캐시에서 주가 데이터 조회 (메모리 → 디스크 순)

        @param stock_code: 종목 코드 (예: "005930")
        @return: OHLCV DataFrame 또는 None (캐시 미스)
        """
        today = self._today_str()

        # 1단계: 메모리 캐시
        mem = self._memory_cache.get(stock_code)
        if mem and mem.get('fetchDate') == today:
            logger.debug(f"[Cache HIT - memory] {stock_code}")
            return mem['data']

        # 2단계: 디스크 캐시
        disk_data = self._load_from_disk(stock_code, today)
        if disk_data is not None:
            # 메모리 캐시 복원
            self._memory_cache[stock_code] = {
                'fetchDate': today,
                'data': disk_data
            }
            logger.info(f"[Cache HIT - disk] {stock_code}")
            return disk_data

        # 캐시 미스
        logger.info(f"[Cache MISS] {stock_code}")
        return None

    def put(self, stock_code: str, df: pd.DataFrame):
        """
        캐시에 주가 데이터 저장 (메모리 + 디스크 동시)

        @param stock_code: 종목 코드
        @param df: OHLCV DataFrame
        """
        today = self._today_str()

        # 메모리 캐시 저장
        self._memory_cache[stock_code] = {
            'fetchDate': today,
            'data': df
        }

        # 디스크 캐시 저장
        self._save_to_disk(stock_code, today, df)

        logger.info(f"[Cache PUT] {stock_code} ({len(df)} records, date={today})")

    def invalidate(self, stock_code: str):
        """특정 종목 캐시 무효화"""
        self._memory_cache.pop(stock_code, None)
        self._delete_from_disk(stock_code)
        logger.info(f"[Cache INVALIDATE] {stock_code}")

    def invalidate_all(self):
        """전체 캐시 무효화"""
        self._memory_cache.clear()
        conn = sqlite3.connect(self.cache_db_path)
        try:
            conn.execute("DELETE FROM price_cache")
            conn.commit()
        finally:
            conn.close()
        logger.info("[Cache INVALIDATE ALL]")

    def get_stats(self) -> Dict:
        """캐시 통계 조회"""
        today = self._today_str()
        memory_count = sum(
            1 for v in self._memory_cache.values()
            if v.get('fetchDate') == today
        )

        conn = sqlite3.connect(self.cache_db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM price_cache WHERE fetch_date = ?",
                (today,)
            ).fetchone()
            disk_count = row[0] if row else 0
        finally:
            conn.close()

        return {
            'memory_cached': memory_count,
            'disk_cached_today': disk_count,
            'cache_date': today
        }

    # ──────────────────────────────────────────────
    # Ticker 캐시
    # ──────────────────────────────────────────────

    def get_ticker(self, stock_code: str) -> Optional[str]:
        """캐시에서 ticker 결과 조회 (일일 1회)"""
        today = self._today_str()
        conn = sqlite3.connect(self.cache_db_path)
        try:
            row = conn.execute(
                "SELECT ticker FROM ticker_cache WHERE stock_code = ? AND fetch_date = ?",
                (stock_code, today)
            ).fetchone()
            if row:
                logger.debug(f"[Ticker Cache HIT] {stock_code} → {row[0]}")
                return row[0]
        finally:
            conn.close()
        return None

    def put_ticker(self, stock_code: str, ticker: str):
        """ticker 결과 캐시 저장"""
        today = self._today_str()
        conn = sqlite3.connect(self.cache_db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO ticker_cache (stock_code, ticker, fetch_date)
                   VALUES (?, ?, ?)""",
                (stock_code, ticker, today)
            )
            conn.commit()
            logger.debug(f"[Ticker Cache PUT] {stock_code} → {ticker}")
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 디스크 캐시 내부 메서드
    # ──────────────────────────────────────────────

    def _load_from_disk(self, stock_code: str, fetch_date: str) -> Optional[pd.DataFrame]:
        """디스크 캐시에서 데이터 로드"""
        conn = sqlite3.connect(self.cache_db_path)
        try:
            row = conn.execute(
                "SELECT data_json FROM price_cache WHERE stock_code = ? AND fetch_date = ?",
                (stock_code, fetch_date)
            ).fetchone()

            if not row:
                return None

            data = json.loads(row[0])
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            return df

        except Exception as e:
            logger.error(f"Failed to load disk cache for {stock_code}: {e}")
            return None
        finally:
            conn.close()

    def _save_to_disk(self, stock_code: str, fetch_date: str, df: pd.DataFrame):
        """디스크 캐시에 데이터 저장"""
        conn = sqlite3.connect(self.cache_db_path)
        try:
            # DataFrame → JSON (Date를 문자열로 변환)
            df_copy = df.copy()
            df_copy['Date'] = df_copy['Date'].astype(str)
            data_json = df_copy.to_dict(orient='list')
            json_str = json.dumps(data_json, ensure_ascii=False)

            conn.execute(
                """INSERT OR REPLACE INTO price_cache (stock_code, fetch_date, data_json)
                   VALUES (?, ?, ?)""",
                (stock_code, fetch_date, json_str)
            )
            conn.commit()

        except Exception as e:
            logger.error(f"Failed to save disk cache for {stock_code}: {e}")
        finally:
            conn.close()

    def _delete_from_disk(self, stock_code: str):
        """디스크 캐시에서 데이터 삭제"""
        conn = sqlite3.connect(self.cache_db_path)
        try:
            conn.execute(
                "DELETE FROM price_cache WHERE stock_code = ?",
                (stock_code,)
            )
            conn.commit()
        finally:
            conn.close()

    def cleanup_old_cache(self, keep_days: int = 3):
        """오래된 캐시 정리 (기본: 3일 이전 데이터 삭제)"""
        from datetime import timedelta
        cutoff = (date.today() - timedelta(days=keep_days)).isoformat()

        conn = sqlite3.connect(self.cache_db_path)
        try:
            result = conn.execute(
                "DELETE FROM price_cache WHERE fetch_date < ?",
                (cutoff,)
            )
            deleted = result.rowcount
            conn.execute(
                "DELETE FROM ticker_cache WHERE fetch_date < ?",
                (cutoff,)
            )
            conn.commit()
            if deleted > 0:
                logger.info(f"[Cache CLEANUP] Removed {deleted} old entries (before {cutoff})")
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 유틸
    # ──────────────────────────────────────────────

    @staticmethod
    def _today_str() -> str:
        """오늘 날짜 문자열 반환 (YYYY-MM-DD)"""
        return date.today().isoformat()


# 모듈 레벨 싱글턴 (worker 프로세스 내에서 공유)
_global_cache: Optional[DataCache] = None


def get_cache() -> DataCache:
    """글로벌 DataCache 인스턴스 반환 (싱글턴)"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DataCache()
    return _global_cache
