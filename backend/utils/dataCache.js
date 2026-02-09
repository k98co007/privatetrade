/**
 * DataCache - 주가 데이터 캐시 모듈 (SRS NFR-301 준수)
 * 
 * 역할: Yahoo Finance 데이터를 일일 1회만 수집하고, 이후 캐시에서 재사용
 * 캐시 전략:
 *   1단계: 메모리 캐시 (가장 빠름)
 *   2단계: 디스크 캐시 - JSON 파일 (서버 재시작 시에도 당일 데이터 유지)
 *   3단계: Yahoo Finance API 호출 (캐시 미스 시에만)
 * 
 * 캐시 갱신 조건: fetchDate가 당일(00:00 이후)이면 캐시 사용, 아니면 재수집
 */

const fs = require('fs');
const path = require('path');

// 디스크 캐시 디렉토리
const CACHE_DIR = path.join(__dirname, '..', '..', 'data', 'cache');

class DataCache {
  constructor(cacheDir = CACHE_DIR) {
    this.cacheDir = cacheDir;

    // 1계층: 메모리 캐시 { stockCode: { fetchDate, data, timestamp } }
    this._memoryCache = new Map();

    // 디스크 캐시 디렉토리 생성
    this._ensureCacheDir();

    console.log(`[DataCache] Initialized (disk: ${this.cacheDir})`);
  }

  // ──────────────────────────────────────────────
  // 공개 API
  // ──────────────────────────────────────────────

  /**
   * 캐시에서 주가 데이터 조회 (메모리 → 디스크 순)
   * @param {string} stockCode - 종목 코드 (예: "005930")
   * @returns {object|null} OHLCV 데이터 또는 null (캐시 미스)
   */
  get(stockCode) {
    const today = this._todayStr();

    // 1단계: 메모리 캐시
    const mem = this._memoryCache.get(stockCode);
    if (mem && mem.fetchDate === today) {
      console.log(`[DataCache] HIT (memory) ${stockCode}`);
      return mem.data;
    }

    // 2단계: 디스크 캐시
    const diskData = this._loadFromDisk(stockCode, today);
    if (diskData !== null) {
      // 메모리 캐시 복원
      this._memoryCache.set(stockCode, {
        fetchDate: today,
        data: diskData,
        timestamp: Date.now()
      });
      console.log(`[DataCache] HIT (disk) ${stockCode}`);
      return diskData;
    }

    // 캐시 미스
    console.log(`[DataCache] MISS ${stockCode}`);
    return null;
  }

  /**
   * 캐시에 주가 데이터 저장 (메모리 + 디스크 동시)
   * @param {string} stockCode - 종목 코드
   * @param {object} data - OHLCV 데이터 ({ dates, opens, highs, lows, closes, volumes })
   */
  put(stockCode, data) {
    const today = this._todayStr();

    // 메모리 캐시 저장
    this._memoryCache.set(stockCode, {
      fetchDate: today,
      data: data,
      timestamp: Date.now()
    });

    // 디스크 캐시 저장
    this._saveToDisk(stockCode, today, data);

    console.log(`[DataCache] PUT ${stockCode} (date=${today})`);
  }

  /**
   * 캐시 유효성 확인 (날짜 기반)
   * @param {string} stockCode - 종목 코드
   * @returns {boolean} 당일 캐시 존재 여부
   */
  isCacheValid(stockCode) {
    return this.get(stockCode) !== null;
  }

  /**
   * 특정 종목 캐시 무효화
   * @param {string} stockCode
   */
  invalidate(stockCode) {
    this._memoryCache.delete(stockCode);
    this._deleteFromDisk(stockCode);
    console.log(`[DataCache] INVALIDATE ${stockCode}`);
  }

  /**
   * 전체 캐시 무효화
   */
  invalidateAll() {
    this._memoryCache.clear();
    try {
      if (fs.existsSync(this.cacheDir)) {
        const files = fs.readdirSync(this.cacheDir);
        for (const file of files) {
          if (file.endsWith('.json')) {
            fs.unlinkSync(path.join(this.cacheDir, file));
          }
        }
      }
    } catch (err) {
      console.error('[DataCache] Error clearing disk cache:', err.message);
    }
    console.log('[DataCache] INVALIDATE ALL');
  }

  /**
   * 캐시 통계
   * @returns {object} { memoryCached, diskCachedToday, cacheDate }
   */
  getStats() {
    const today = this._todayStr();

    let memoryCached = 0;
    for (const [, val] of this._memoryCache) {
      if (val.fetchDate === today) memoryCached++;
    }

    let diskCachedToday = 0;
    try {
      if (fs.existsSync(this.cacheDir)) {
        const files = fs.readdirSync(this.cacheDir);
        for (const file of files) {
          if (file.includes(`_${today}`) && file.endsWith('.json')) {
            diskCachedToday++;
          }
        }
      }
    } catch (err) {
      // ignore
    }

    return {
      memory_cached: memoryCached,
      disk_cached_today: diskCachedToday,
      cache_date: today
    };
  }

  /**
   * 오래된 캐시 정리 (기본: 3일 이전 데이터 삭제)
   * @param {number} keepDays - 유지할 일수
   */
  cleanupOldCache(keepDays = 3) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - keepDays);
    const cutoffStr = cutoff.toISOString().split('T')[0];

    let deleted = 0;
    try {
      if (fs.existsSync(this.cacheDir)) {
        const files = fs.readdirSync(this.cacheDir);
        for (const file of files) {
          if (!file.endsWith('.json')) continue;
          // 파일명: {stockCode}_{YYYY-MM-DD}.json
          const match = file.match(/_(\d{4}-\d{2}-\d{2})\.json$/);
          if (match && match[1] < cutoffStr) {
            fs.unlinkSync(path.join(this.cacheDir, file));
            deleted++;
          }
        }
      }
    } catch (err) {
      console.error('[DataCache] Error during cleanup:', err.message);
    }

    if (deleted > 0) {
      console.log(`[DataCache] CLEANUP: Removed ${deleted} old entries (before ${cutoffStr})`);
    }
  }

  // ──────────────────────────────────────────────
  // 디스크 캐시 내부 메서드
  // ──────────────────────────────────────────────

  _ensureCacheDir() {
    try {
      if (!fs.existsSync(this.cacheDir)) {
        fs.mkdirSync(this.cacheDir, { recursive: true });
      }
    } catch (err) {
      console.error('[DataCache] Error creating cache dir:', err.message);
    }
  }

  _diskCachePath(stockCode, fetchDate) {
    return path.join(this.cacheDir, `${stockCode}_${fetchDate}.json`);
  }

  _loadFromDisk(stockCode, fetchDate) {
    const filePath = this._diskCachePath(stockCode, fetchDate);
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf8');
        return JSON.parse(raw);
      }
    } catch (err) {
      console.error(`[DataCache] Error reading disk cache for ${stockCode}:`, err.message);
    }
    return null;
  }

  _saveToDisk(stockCode, fetchDate, data) {
    const filePath = this._diskCachePath(stockCode, fetchDate);
    try {
      this._ensureCacheDir();
      fs.writeFileSync(filePath, JSON.stringify(data), 'utf8');
    } catch (err) {
      console.error(`[DataCache] Error writing disk cache for ${stockCode}:`, err.message);
    }
  }

  _deleteFromDisk(stockCode) {
    try {
      if (fs.existsSync(this.cacheDir)) {
        const files = fs.readdirSync(this.cacheDir);
        for (const file of files) {
          if (file.startsWith(`${stockCode}_`) && file.endsWith('.json')) {
            fs.unlinkSync(path.join(this.cacheDir, file));
          }
        }
      }
    } catch (err) {
      console.error(`[DataCache] Error deleting disk cache for ${stockCode}:`, err.message);
    }
  }

  // ──────────────────────────────────────────────
  // 유틸
  // ──────────────────────────────────────────────

  _todayStr() {
    return new Date().toISOString().split('T')[0];
  }
}

// 싱글턴 인스턴스
let _globalCache = null;

function getCache() {
  if (!_globalCache) {
    _globalCache = new DataCache();
  }
  return _globalCache;
}

module.exports = { DataCache, getCache };
