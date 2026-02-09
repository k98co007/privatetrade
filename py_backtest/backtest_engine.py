"""
BacktestEngine - 주식 백테스팅 엔진
역할: 주가 데이터 기반 매매 시뮬레이션 및 성과 지표 계산
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import logging
import sys

# 데이터 캐시 모듈 (SRS NFR-301: 일일 1회 수집)
try:
    from data_cache import get_cache
    HAS_CACHE = True
except ImportError:
    try:
        from .data_cache import get_cache
        HAS_CACHE = True
    except ImportError:
        HAS_CACHE = False
        get_cache = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# yfinance 임포트
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    logger.warning("yfinance not installed. Install with: pip install yfinance")
    yf = None


@dataclass
class Position:
    """포지션 정보"""
    entry_date: str
    entry_price: float
    quantity: int
    type: str = 'long'


@dataclass
class Trade:
    """거래 기록"""
    date: str
    type: str  # 'BUY' or 'SELL'
    price: float
    quantity: int
    cost_or_proceeds: float
    profit: Optional[float] = None
    profit_rate: Optional[float] = None
    cash_remaining: float = 0


@dataclass
class Strategy1Trade:
    """전략 1 거래 기록 (LLD 3.3.2 준수)"""
    buy_time: str
    buy_price: float
    sell_time: str
    sell_price: float
    buy_amount: float      # 투입 금액
    gross_profit: float     # 매매 차익
    cost: float             # 세금 + 수수료
    profit: float           # 순수익 (net_profit)
    balance_after: float    # 거래 후 잔고


@dataclass
class Strategy2Trade:
    """전략 2 거래 기록 (LLD 3.3.3 Trailing Stop 준수)"""
    buy_time: str
    buy_price: float
    sell_time: str
    sell_price: float
    buy_amount: float           # 투입 금액
    gross_profit: float          # 매매 차익
    cost: float                  # 세금 + 수수료
    profit: float                # 순수익 (net_profit)
    balance_after: float         # 거래 후 잔고
    sell_reason: str = ''        # 매도 사유: 'trailing_stop', 'loss_cutoff', 'end_of_day'
    highest_price: float = 0.0   # 트레일링 중 최고가
    max_profit_pct: float = 0.0  # 최대 수익률(%)


class BacktestEngine:
    """
    주식 백테스팅 엔진
    - 특정 기간의 주가 데이터를 기반으로 매매 시뮬레이션
    - 수익률, 승률, MDD 등 성과 지표 계산
    """
    
    def __init__(self, stock_code: str, initial_capital: float = 10000000):
        """
        @param stock_code: 종목 코드 (예: "005930")
        @param initial_capital: 초기 자본금 (기본값: 1천만원)
        """
        self.stock_code = stock_code
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.positions: List[Position] = []
        self.trading_log: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        logger.info(f"BacktestEngine initialized for {stock_code} with capital {initial_capital}")
    
    def load_price_data(self, prices_dict: Optional[Dict] = None, period: int = 60) -> pd.DataFrame:
        """
        주가 데이터 로드 (2가지 방식 지원)
        
        방식 1: prices_dict 전달 (Node.js Backend에서 이미 수집한 데이터)
        - prices_dict: {"dates": [...], "opens": [...], ...}
        
        방식 2: Yahoo Finance에서 직접 조회
        - period: 조회 기간 (일 단위)
        
        @param prices_dict: Node.js에서 전달받은 OHLCV 데이터 (선택사항)
        @param period: Yahoo Finance 조회 기간 (기본값: 60일)
        @return: OHLCV 데이터프레임
        """
        try:
            # 방식 1: prices_dict가 전달된 경우 (Backend 데이터 사용)
            if prices_dict and prices_dict.get('dates'):
                logger.info(f"Using prices data from Backend (Node.js): {len(prices_dict.get('dates', []))} records")
                df = pd.DataFrame({
                    'Date': prices_dict.get('dates', []),
                    'Open': prices_dict.get('opens', []),
                    'High': prices_dict.get('highs', []),
                    'Low': prices_dict.get('lows', []),
                    'Close': prices_dict.get('closes', []),
                    'Volume': prices_dict.get('volumes', [])
                })
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date').reset_index(drop=True)
                logger.info(f"Loaded {len(df)} price records from Backend")
                return df
            
            # 방식 2: 캐시 확인 → Yahoo Finance 조회 (SRS NFR-301: 일일 1회 수집)
            # 3단계 조회: 메모리 캐시 → 디스크 캐시 → Yahoo Finance API
            
            # 2-1. 캐시에서 당일 데이터 조회
            if HAS_CACHE and get_cache is not None:
                cache = get_cache()
                cached_df = cache.get(self.stock_code)
                if cached_df is not None:
                    logger.info(f"Using cached price data for {self.stock_code} ({len(cached_df)} records)")
                    return cached_df
            
            # 2-2. 캐시 미스 → Yahoo Finance에서 직접 조회
            logger.info(f"Fetching data from Yahoo Finance for {self.stock_code} (period={period}d)...")
            
            if not HAS_YFINANCE or yf is None:
                raise ImportError(
                    "yfinance is not installed and prices_dict not provided. "
                    "Either install yfinance with 'pip install yfinance' "
                    "or provide prices_dict from Backend"
                )
            
            # 종목 코드를 Yahoo Finance Ticker로 변환 (캐시 활용)
            ticker = self._convert_to_ticker_safe(self.stock_code)
            logger.info(f"Converted stock code {self.stock_code} to ticker: {ticker}")
            
            # Yahoo Finance에서 분봉 데이터 조회 시도
            # yf.Ticker().history() 사용 (yf.download()는 MultiIndex 컬럼 문제 있음)
            try:
                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(
                    period=f"{period}d",
                    interval="2m"
                )
                
                if df.empty:
                    logger.warning(f"No data for {ticker}, trying alternative format...")
                    # 다른 형식 시도 (예: 대문자)
                    ticker_alt = ticker.upper()
                    ticker_obj = yf.Ticker(ticker_alt)
                    df = ticker_obj.history(
                        period=f"{period}d",
                        interval="2m"
                    )
                
                if df.empty:
                    raise ValueError(f"No data available for {ticker}")
                
            except Exception as yf_error:
                logger.error(f"Yahoo Finance error for {ticker}: {str(yf_error)}")
                # Yahoo Finance 실패 시, 테스트 데이터로 대체 (개발용)
                logger.warning("Using mock data for development/testing")
                return self._generate_mock_data()
            
            # 인덱스를 Date 컬럼으로 변환
            # Ticker.history()는 인트라데이 데이터의 인덱스명이 'Datetime'
            df = df.reset_index()
            # 인덱스 컬럼명이 'Datetime' 또는 'Date'일 수 있음
            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            df = df.rename(columns={date_col: 'Date'})
            # 필요한 OHLCV 컬럼만 선택
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            
            # 2-3. Yahoo Finance에서 수집한 데이터를 캐시에 저장 (일일 1회)
            if HAS_CACHE and get_cache is not None:
                cache = get_cache()
                cache.put(self.stock_code, df)
                logger.info(f"Cached price data for {self.stock_code} (daily cache)")
            
            logger.info(f"Loaded {len(df)} price records from Yahoo Finance")
            return df
            
        except Exception as e:
            logger.error(f"Error loading price data: {str(e)}")
            raise ValueError(f"Failed to load price data: {str(e)}")
    
    def _convert_to_ticker_safe(self, stock_code: str, market: str = None) -> str:
        """
        한국 종목 코드를 Yahoo Finance Ticker로 변환 (개선된 버전)
        
        @param stock_code: KRX 종목 코드 (예: "005930" = 삼성전자)
        @param market: 시장 구분 ('KS'=KOSPI, 'KQ'=KOSDAQ, None=자동감지)
        @return: Yahoo Finance Ticker (예: "005930.KS")
        
        한국 종목 코드는 숫자 범위로 KOSPI/KOSDAQ를 구별할 수 없음.
        예: 005930(삼성전자)=KOSPI, 035420(NAVER)=KOSPI 모두 숫자값이 4000 이상.
        따라서 market 파라미터로 명시하거나, yfinance로 실제 조회하여 판별.
        """
        # 1. market이 명시된 경우 바로 반환
        if market in ('KS', 'KQ'):
            ticker = f"{stock_code}.{market}"
            logger.debug(f"Converted {stock_code} → {ticker} (market specified)")
            return ticker
        
        # 2. ticker 캐시 확인 (일일 1회 - 동일 종목의 반복 조회 방지)
        if HAS_CACHE and get_cache is not None:
            cache = get_cache()
            cached_ticker = cache.get_ticker(stock_code)
            if cached_ticker:
                logger.info(f"Resolved {stock_code} → {cached_ticker} (from cache)")
                return cached_ticker
        
        # 3. market 미지정 시: .KS(KOSPI) 우선 시도, 실패 시 .KQ(KOSDAQ)
        #    대부분의 대형 종목(KOSPI 200 등)은 KOSPI이므로 .KS 우선
        resolved_ticker = None
        if HAS_YFINANCE and yf is not None:
            for suffix in ['KS', 'KQ']:
                candidate = f"{stock_code}.{suffix}"
                try:
                    info = yf.Ticker(candidate)
                    # fast_info 또는 history로 유효성 확인
                    hist = info.history(period='1d')
                    if hist is not None and not hist.empty:
                        logger.info(f"Resolved {stock_code} → {candidate} (auto-detected)")
                        resolved_ticker = candidate
                        break
                except Exception:
                    continue
        
        # 4. yfinance 미설치이거나 조회 실패 시 기본값 .KS 사용
        if not resolved_ticker:
            resolved_ticker = f"{stock_code}.KS"
            logger.warning(f"Could not auto-detect market for {stock_code}, defaulting to {resolved_ticker}")
        
        # 5. 결과를 ticker 캐시에 저장
        if HAS_CACHE and get_cache is not None:
            cache = get_cache()
            cache.put_ticker(stock_code, resolved_ticker)
        
        return resolved_ticker
    
    def _convert_to_ticker(self, stock_code: str, market: str = None) -> str:
        """레거시 메서드 (호환성 유지)"""
        return self._convert_to_ticker_safe(stock_code, market)
    
    def _generate_mock_data(self, num_records: int = 200) -> pd.DataFrame:
        """
        테스트용 Mock 데이터 생성
        개발/테스트 환경에서 Yahoo Finance 대신 사용
        
        @param num_records: 생성할 데이터 포인트 수
        @return: Mock OHLCV 데이터프레임
        """
        logger.warning(f"Generating mock data with {num_records} records")
        
        # 현재 날짜부터 과거로 num_records개의 2분 봉 생성
        end_date = datetime.now()
        dates = [end_date - timedelta(minutes=2*i) for i in range(num_records)]
        dates.reverse()
        
        # 가격 데이터 시뮬레이션 (시작가: 70000원, 변동성 있음)
        np.random.seed(42)
        base_price = 70000
        returns = np.random.normal(0, 0.001, num_records)
        closes = base_price * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'Date': dates,
            'Close': closes,
            'Open': closes * (1 + np.random.uniform(-0.002, 0.002, num_records)),
            'High': closes * (1 + np.random.uniform(0, 0.003, num_records)),
            'Low': closes * (1 - np.random.uniform(0, 0.003, num_records)),
            'Volume': np.random.uniform(10000, 100000, num_records).astype(int)
        })
        
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        logger.info(f"Mock data generated: {len(df)} records, {df['Date'].min()} to {df['Date'].max()}")
        return df
    
    def run_backtest(self, strategy: Dict, prices_dict: Optional[Dict] = None, period: int = 60) -> Dict:
        """
        백테스팅 실행 (전략 유형에 따라 분기)
        
        @param strategy: 전략 설정
        @param prices_dict: Node.js Backend에서 전달받은 주가 데이터
        @param period: 조회 기간 (일 단위, 기본값: 60일)
        @return: 백테스팅 결과
        """
        strategy_type = strategy.get('type', strategy.get('signal_type', ''))
        
        logger.info(
            f"run_backtest called | stock={self.stock_code} | "
            f"strategy_type={strategy_type!r} | period={period}d | "
            f"capital={self.initial_capital:,.0f} | "
            f"prices_dict={'provided ('+str(len(prices_dict.get('dates',[])))+'rec)' if prices_dict and prices_dict.get('dates') else 'None'} | "
            f"strategy_params={strategy}"
        )
        
        # 전략 1: 고정시간 매수/매도 (LLD 3.3.2)
        if strategy_type in ('daily_trading', 'strategy1', 'fixed_time'):
            return self.run_strategy1_backtest(strategy, prices_dict, period)
        
        # 전략 2: Trailing Stop (LLD 3.3.3)
        if strategy_type in ('trailing_stop', 'strategy2'):
            return self.run_strategy2_backtest(strategy, prices_dict, period)
        
        # 기존 방식 (레거시 호환)
        logger.info(f"Falling back to legacy backtest (strategy_type={strategy_type!r} not matched)")
        return self._run_legacy_backtest(strategy, prices_dict, period)
    
    def run_strategy1_backtest(self, strategy: Dict, prices_dict: Optional[Dict] = None, period: int = 60) -> Dict:
        """
        전략 1: 고정시간 매수/매도 백테스팅 (LLD 3.3.2 준수)
        
        매일 지정된 시간에 매수하고, 지정된 시간에 매도.
        누적 손실(lossAmount)을 추적하여 투입 금액(buyAmount)에 반영.
        세금(0.2%) + 수수료(0.011%) 비용 적용.
        
        @param strategy: {"buy_time": "10:00", "sell_time": "15:00", "type": "daily_trading"}
        @param prices_dict: 주가 데이터 (없으면 Yahoo Finance에서 조회)
        @param period: 조회 기간 (일)
        @return: 백테스팅 결과
        """
        try:
            # 1. 주가 데이터 로드
            prices = self.load_price_data(prices_dict=prices_dict, period=period)
            
            # 2. 전략 1 실행
            buy_time = strategy.get('buy_time', '10:00')
            sell_time = strategy.get('sell_time', '15:00')
            
            # 데이터 특성 로깅
            date_range = f"{prices['Date'].min()} ~ {prices['Date'].max()}" if len(prices) > 0 else 'empty'
            unique_dates = prices['Date'].dt.date.nunique() if len(prices) > 0 else 0
            logger.info(
                f"Strategy 1 backtest starting | stock={self.stock_code} | "
                f"buy_time={buy_time} | sell_time={sell_time} | "
                f"seed_money={self.initial_capital:,.0f} | "
                f"records={len(prices)} | trading_days={unique_dates} | "
                f"date_range=[{date_range}]"
            )
            
            trades = self.execute_strategy1(
                buy_time=buy_time,
                sell_time=sell_time,
                ohlc_data=prices,
                seed_money=self.initial_capital
            )
            
            logger.info(f"Strategy 1 completed: {len(trades)} trades")
            
            # 3. 결과 계산
            return self._calculate_strategy1_performance(trades)
            
        except Exception as e:
            logger.error(f"Strategy 1 backtest error: {str(e)}")
            raise
    
    def _find_nearest_candle(self, day_data: pd.DataFrame, target_time: str, direction: str = 'backward') -> Optional[pd.Series]:
        """
        지정된 시간에 가장 가까운 캔들 찾기
        
        2분봉 데이터에서 정확한 시간이 없을 수 있으므로 (예: 15:00 → 14:58),
        가장 가까운 캔들을 찾아 반환한다.
        
        @param day_data: 당일 OHLCV 데이터 (time_str 컬럼 필요)
        @param target_time: 목표 시간 (예: "15:00")
        @param direction: 'backward' = 목표 시간 이하 중 가장 늦은 캔들,
                          'forward' = 목표 시간 이상 중 가장 빠른 캔들
        @return: 매칭된 캔들 (Series) 또는 None
        """
        if day_data.empty:
            return None
        
        # 1. 정확히 일치하는 캔들이 있으면 바로 반환
        exact = day_data[day_data['time_str'] == target_time]
        if not exact.empty:
            return exact.iloc[0]
        
        # 2. 가장 가까운 캔들 탐색 (정확한 시간이 없을 때 fallback)
        if direction == 'backward':
            # target_time 이하인 캔들 중 가장 늦은 것
            candidates = day_data[day_data['time_str'] <= target_time]
            if not candidates.empty:
                matched = candidates.iloc[-1]
                logger.debug(
                    f"Nearest candle (backward): target={target_time} → matched={matched['time_str']} "
                    f"(Close={matched['Close']})"
                )
                return matched
            # target_time보다 이른 캔들이 없으면 가장 빠른 캔들 반환
            fallback = day_data.iloc[0]
            logger.debug(
                f"Nearest candle (backward fallback): target={target_time} → first candle={fallback['time_str']} "
                f"(Close={fallback['Close']})"
            )
            return fallback
        else:  # forward
            # target_time 이상인 캔들 중 가장 빠른 것
            candidates = day_data[day_data['time_str'] >= target_time]
            if not candidates.empty:
                matched = candidates.iloc[0]
                logger.debug(
                    f"Nearest candle (forward): target={target_time} → matched={matched['time_str']} "
                    f"(Close={matched['Close']})"
                )
                return matched
            # target_time보다 늦은 캔들이 없으면 마지막 캔들 반환
            fallback = day_data.iloc[-1]
            logger.debug(
                f"Nearest candle (forward fallback): target={target_time} → last candle={fallback['time_str']} "
                f"(Close={fallback['Close']})"
            )
            return fallback

    def execute_strategy1(self, buy_time: str, sell_time: str, 
                           ohlc_data: pd.DataFrame, seed_money: float) -> List[Strategy1Trade]:
        """
        전략 1: 고정시간 매수/매도 (LLD 3.3.2 준수)
        
        의사코드:
          balance = seedMoney
          lossAmount = 0  // 누적 손해액
          
          for each day:
            buyCandle = day.find(candle.time === buy_time)
            sellCandle = day.find(candle.time === sell_time)
            buyPrice = buyCandle.close
            buyAmount = balance - lossAmount
            sellPrice = sellCandle.close
            grossProfit = (sellPrice - buyPrice) * (buyAmount / buyPrice)
            cost = sellPrice * buyAmount * 0.2% + sellPrice * buyAmount * 0.011%
            netProfit = grossProfit - cost
            balance += netProfit
            if netProfit < 0: lossAmount += abs(netProfit)
        
        @param buy_time: 매수 시간 (예: "10:00")
        @param sell_time: 매도 시간 (예: "15:00")
        @param ohlc_data: OHLCV 데이터프레임 (Date, Open, High, Low, Close, Volume)
        @param seed_money: 씨드머니 (초기 자본금)
        @return: 거래 기록 리스트
        """
        trades: List[Strategy1Trade] = []
        balance = seed_money
        loss_amount = 0.0  # 누적 손해액
        
        logger.info(
            f"execute_strategy1 | buy_time={buy_time} | sell_time={sell_time} | "
            f"seed_money={seed_money:,.0f} | records={len(ohlc_data)}"
        )
        
        # 날짜별로 그룹핑
        ohlc_data = ohlc_data.copy()
        ohlc_data['Date'] = pd.to_datetime(ohlc_data['Date'])
        ohlc_data['trade_date'] = ohlc_data['Date'].dt.date
        ohlc_data['time_str'] = ohlc_data['Date'].dt.strftime('%H:%M')
        
        grouped = ohlc_data.groupby('trade_date')
        total_days = len(grouped)
        skipped_days = 0
        
        # 데이터에 존재하는 시간 범위 로깅 (첫 번째 날 기준)
        first_day = list(grouped)[0][1] if total_days > 0 else pd.DataFrame()
        if not first_day.empty:
            avail_times = sorted(first_day['time_str'].unique())
            logger.info(
                f"Available candle times (day1): {avail_times[0]}~{avail_times[-1]} "
                f"({len(avail_times)} slots, interval={avail_times[1] if len(avail_times)>1 else 'N/A'}~) | "
                f"buy_time={buy_time} in data: {buy_time in avail_times} | "
                f"sell_time={sell_time} in data: {sell_time in avail_times}"
            )
        
        for date, day_data in grouped:
            day_data_sorted = day_data.sort_values('Date')
            
            # 매수 시점 찾기 (정확 매칭 → 근접 매칭 fallback)
            buy_candle = self._find_nearest_candle(day_data_sorted, buy_time, direction='forward')
            if buy_candle is None:
                skipped_days += 1
                logger.debug(f"{date}: No candle near buy_time {buy_time}, skipping")
                continue
            
            buy_price = float(buy_candle['Close'])
            
            if buy_price <= 0:
                logger.warning(f"{date}: Invalid buy price {buy_price}, skipping")
                continue
            
            # 투입 금액 = balance - lossAmount (LLD 명세)
            buy_amount = balance - loss_amount
            if buy_amount <= 0:
                logger.warning(f"{date}: buyAmount <= 0 (balance={balance}, lossAmount={loss_amount}), skipping")
                continue
            
            # 매도 시점 찾기 (정확 매칭 → 근접 매칭 fallback)
            sell_candle = self._find_nearest_candle(day_data_sorted, sell_time, direction='backward')
            if sell_candle is None:
                skipped_days += 1
                logger.debug(f"{date}: No candle near sell_time {sell_time}, skipping")
                continue
            sell_price = float(sell_candle['Close'])
            
            # 실제 매칭된 시간 로깅 (target vs actual)
            actual_buy_time = buy_candle['time_str']
            actual_sell_time = sell_candle['time_str']
            if actual_buy_time != buy_time or actual_sell_time != sell_time:
                logger.debug(
                    f"{date}: Time adjusted | buy {buy_time}→{actual_buy_time} | sell {sell_time}→{actual_sell_time}"
                )
            
            if sell_price <= 0:
                logger.warning(f"{date}: Invalid sell price {sell_price}, skipping")
                continue
            
            # 거래 결과 계산 (LLD 3.3.2)
            # grossProfit = (sellPrice - buyPrice) * (buyAmount / buyPrice)
            gross_profit = (sell_price - buy_price) * (buy_amount / buy_price)
            
            # 비용 = 세금(매도금액의 0.2%) + 수수료(매도금액의 0.011%)
            # 매도금액 = sellPrice * (buyAmount / buyPrice) = 보유 주식의 매도 총액
            sell_total = sell_price * (buy_amount / buy_price)
            tax = sell_total * 0.2 / 100
            commission = sell_total * 0.011 / 100
            cost = tax + commission
            
            # 순수익
            net_profit = gross_profit - cost
            
            # 잔고 업데이트
            balance += net_profit
            
            # 손실 시 누적 손해액 증가
            if net_profit < 0:
                loss_amount += abs(net_profit)
            
            # 거래 기록
            trade = Strategy1Trade(
                buy_time=str(buy_candle['Date']),
                buy_price=buy_price,
                sell_time=str(sell_candle['Date']),
                sell_price=sell_price,
                buy_amount=buy_amount,
                gross_profit=gross_profit,
                cost=cost,
                profit=net_profit,
                balance_after=balance
            )
            trades.append(trade)
            
            logger.info(
                f"[S1 Trade #{len(trades)}] {date} | "
                f"BUY@{buy_price:,.0f}({buy_candle['time_str']}) → SELL@{sell_price:,.0f}({sell_candle['time_str']}) | "
                f"qty={buy_amount/buy_price:.0f}주 buyAmt={buy_amount:,.0f} | "
                f"gross={gross_profit:+,.0f} cost={cost:,.0f} net={net_profit:+,.0f} | "
                f"bal={balance:,.0f} lossAmt={loss_amount:,.0f}"
            )
        
        logger.info(
            f"Strategy 1 finished | trades={len(trades)}/{total_days}days "
            f"(skipped={skipped_days}) | "
            f"final_balance={balance:,.0f} | total_loss_amount={loss_amount:,.0f}"
        )
        return trades
    
    def _calculate_strategy1_performance(self, trades: List[Strategy1Trade]) -> Dict:
        """
        전략 1 성과 지표 계산
        
        @param trades: Strategy1Trade 리스트
        @return: 성과 요약 딕셔너리
        """
        if not trades:
            return {
                'stock_code': self.stock_code,
                'strategy': 'strategy1_fixed_time',
                'total_profit': 0.0,
                'return_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'mdd': 0.0,
                'total_cost': 0.0,
                'initial_capital': float(self.initial_capital),
                'final_capital': float(self.initial_capital),
                'trading_log': [],
                'equity_curve': [float(self.initial_capital)]
            }
        
        # 승/패 분류
        winning = [t for t in trades if t.profit > 0]
        losing = [t for t in trades if t.profit <= 0]
        
        total_profit = sum(t.profit for t in trades)
        total_cost = sum(t.cost for t in trades)
        total_wins = sum(t.profit for t in winning)
        total_losses = sum(abs(t.profit) for t in losing)
        
        final_balance = trades[-1].balance_after
        return_rate = (total_profit / self.initial_capital) * 100
        win_rate = (len(winning) / len(trades)) * 100 if trades else 0
        avg_win = total_wins / len(winning) if winning else 0
        avg_loss = total_losses / len(losing) if losing else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # 자산 곡선 (equity curve)
        equity_curve = [float(self.initial_capital)]
        for t in trades:
            equity_curve.append(float(t.balance_after))
        
        # MDD 계산
        mdd = self.calculate_mdd(equity_curve)
        
        # 거래 로그 (직렬화 가능 형태)
        trading_log = [asdict(t) for t in trades]
        
        result = {
            'stock_code': self.stock_code,
            'strategy': 'strategy1_fixed_time',
            'total_profit': float(total_profit),
            'return_rate': float(return_rate),
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'mdd': float(mdd),
            'total_cost': float(total_cost),
            'initial_capital': float(self.initial_capital),
            'final_capital': float(final_balance),
            'trading_log': trading_log,
            'equity_curve': equity_curve
        }
        
        logger.info(
            f"Strategy 1 results: {self.stock_code} | "
            f"Return={return_rate:+.2f}% | PnL={total_profit:+,.0f} | "
            f"Trades={len(trades)} (W:{len(winning)} L:{len(losing)}) | "
            f"WinRate={win_rate:.1f}% | AvgWin={avg_win:,.0f} AvgLoss={avg_loss:,.0f} | "
            f"PF={profit_factor:.2f} | MDD={mdd:.2f}% | Cost={total_cost:,.0f} | "
            f"Capital: {self.initial_capital:,.0f} → {final_balance:,.0f}"
        )
        return result
    
    def run_strategy2_backtest(self, strategy: Dict, prices_dict: Optional[Dict] = None, period: int = 60) -> Dict:
        """
        전략 2: Trailing Stop 백테스팅 (LLD 3.3.3 준수)
        
        당일 지정 시간에 매수 → 다음날 Trailing Stop 로직으로 매도.
        - 최소 수익률(min_profit_pct) 도달 시 트레일링 스탑 활성화
        - 고점 대비 profit_cutoff_pct만큼 하락 시 매도
        - 손절 시간(loss_cutoff_time)까지 최소 수익 미달 시 손절
        - 다음날 장 끝까지 미청산 시 종가 매도
        
        @param strategy: {
            "buy_time": "15:30",
            "min_profit_pct": 1.0,
            "profit_cutoff_pct": 80.0,
            "loss_cutoff_time": "14:00",
            "type": "trailing_stop"
        }
        @param prices_dict: 주가 데이터 (없으면 Yahoo Finance에서 조회)
        @param period: 조회 기간 (일)
        @return: 백테스팅 결과
        """
        try:
            # 1. 주가 데이터 로드
            prices = self.load_price_data(prices_dict=prices_dict, period=period)
            
            # 2. 전략 2 실행
            buy_time = strategy.get('buy_time', '15:30')
            min_profit_pct = float(strategy.get('min_profit_pct', 1.0))
            profit_cutoff_pct = float(strategy.get('profit_cutoff_pct', 80.0))
            loss_cutoff_time = strategy.get('loss_cutoff_time', '14:00')
            
            # 데이터 특성 로깅
            date_range = f"{prices['Date'].min()} ~ {prices['Date'].max()}" if len(prices) > 0 else 'empty'
            unique_dates = prices['Date'].dt.date.nunique() if len(prices) > 0 else 0
            logger.info(
                f"Strategy 2 backtest starting | stock={self.stock_code} | "
                f"buy_time={buy_time} | min_profit={min_profit_pct}% | "
                f"cutoff={profit_cutoff_pct}% | loss_cutoff_time={loss_cutoff_time} | "
                f"seed_money={self.initial_capital:,.0f} | "
                f"records={len(prices)} | trading_days={unique_dates} | "
                f"date_range=[{date_range}]"
            )
            
            trades = self.execute_strategy2(
                buy_time=buy_time,
                min_profit_pct=min_profit_pct,
                profit_cutoff_pct=profit_cutoff_pct,
                loss_cutoff_time=loss_cutoff_time,
                ohlc_data=prices,
                seed_money=self.initial_capital
            )
            
            logger.info(f"Strategy 2 completed: {len(trades)} trades")
            
            # 3. 결과 계산
            return self._calculate_strategy2_performance(trades)
            
        except Exception as e:
            logger.error(f"Strategy 2 backtest error: {str(e)}")
            raise
    
    def execute_strategy2(self, buy_time: str, min_profit_pct: float,
                           profit_cutoff_pct: float, loss_cutoff_time: str,
                           ohlc_data: pd.DataFrame, seed_money: float) -> List[Strategy2Trade]:
        """
        전략 2: Trailing Stop (LLD 3.3.3 준수)
        
        의사코드:
          for each day:
            매수: buy_time에 매수
            다음날:
              각 캔들마다:
                profitRate >= min_profit_pct → minProfitReached, highestPrice 추적
                손절시간 도달 && !minProfitReached → 손절
                minProfitReached && (highestPrice - price) / highestPrice > (1 - profit_cutoff_pct/100) → 익절
              다음날 끝까지 미청산 → 종가 매도
        
        @param buy_time: 매수 시간 (예: "15:30")
        @param min_profit_pct: 최소 수익률 % (예: 1.0)
        @param profit_cutoff_pct: 이익보전 비율 % (예: 80.0, 고점 대비 20% 하락 시 매도)
        @param loss_cutoff_time: 손절 시간 (다음날, 예: "14:00")
        @param ohlc_data: OHLCV 데이터프레임
        @param seed_money: 씨드머니
        @return: 거래 기록 리스트
        """
        trades: List[Strategy2Trade] = []
        balance = seed_money
        loss_amount = 0.0
        
        logger.info(
            f"execute_strategy2 | buy_time={buy_time} | min_profit={min_profit_pct}% | "
            f"cutoff={profit_cutoff_pct}% | loss_cutoff_time={loss_cutoff_time} | "
            f"seed_money={seed_money:,.0f} | records={len(ohlc_data)}"
        )
        
        # 날짜별로 그룹핑
        ohlc_data = ohlc_data.copy()
        ohlc_data['Date'] = pd.to_datetime(ohlc_data['Date'])
        ohlc_data['trade_date'] = ohlc_data['Date'].dt.date
        ohlc_data['time_str'] = ohlc_data['Date'].dt.strftime('%H:%M')
        
        # 날짜 목록 (정렬)
        dates_list = sorted(ohlc_data['trade_date'].unique())
        
        # Trailing stop 하락 임계치: 고점 대비 이만큼 하락하면 매도
        # LLD: (highestPrice - candlePrice) / highestPrice > (1 - profit_cutoff_pct / 100)
        # 예: profit_cutoff_pct=80 → 고점 대비 20% 하락 시 매도
        drop_threshold = 1.0 - profit_cutoff_pct / 100.0
        logger.info(f"Trailing stop drop_threshold={drop_threshold:.4f} (sell when drop > {drop_threshold*100:.1f}% from high)")
        
        for day_idx in range(len(dates_list) - 1):  # 마지막 날은 다음날이 없으므로 제외
            current_date = dates_list[day_idx]
            next_date = dates_list[day_idx + 1]
            
            current_day_data = ohlc_data[ohlc_data['trade_date'] == current_date]
            next_day_data = ohlc_data[ohlc_data['trade_date'] == next_date].sort_values('Date')
            
            if next_day_data.empty:
                continue
            
            # Step 1: 매수 (당일 buy_time) - 정확 매칭 → 근접 매칭 fallback
            current_day_sorted = current_day_data.sort_values('Date')
            buy_candle = self._find_nearest_candle(current_day_sorted, buy_time, direction='backward')
            if buy_candle is None:
                logger.debug(f"{current_date}: No candle near buy_time {buy_time}, skipping")
                continue
            buy_price = float(buy_candle['Close'])
            
            if buy_price <= 0:
                logger.warning(f"{current_date}: Invalid buy price {buy_price}, skipping")
                continue
            
            # 투입 금액 = balance - lossAmount
            buy_amount = balance - loss_amount
            if buy_amount <= 0:
                logger.warning(f"{current_date}: buyAmount <= 0 (balance={balance}, lossAmount={loss_amount}), skipping")
                continue
            
            # Step 2: 다음날 손절/익절 탐색
            sell_price = None
            sell_time_str = None
            sell_reason = ''
            highest_price = buy_price
            max_profit_pct_reached = 0.0
            min_profit_reached = False
            
            for _, candle in next_day_data.iterrows():
                candle_price = float(candle['Close'])
                candle_time = candle['time_str']
                
                if candle_price <= 0:
                    continue
                
                # 수익률 계산
                profit_rate = (candle_price - buy_price) / buy_price * 100
                
                # 최소 수익률 도달 확인
                if profit_rate >= min_profit_pct:
                    min_profit_reached = True
                    if candle_price > highest_price:
                        highest_price = candle_price
                    max_profit_pct_reached = max(max_profit_pct_reached, profit_rate)
                
                # 손절 시간 도달 && 최소 수익 미달 → 손절
                if candle_time >= loss_cutoff_time and not min_profit_reached:
                    # 손절 시간의 캔들 가격으로 매도 (근접 매칭)
                    loss_cutoff_candle = self._find_nearest_candle(
                        next_day_data, loss_cutoff_time, direction='backward'
                    )
                    if loss_cutoff_candle is not None:
                        sell_price = float(loss_cutoff_candle['Close'])
                        sell_time_str = str(loss_cutoff_candle['Date'])
                    else:
                        sell_price = candle_price
                        sell_time_str = str(candle['Date'])
                    sell_reason = 'loss_cutoff'
                    break
                
                # 이익보전(Trailing Stop) 로직
                # (highestPrice - candlePrice) / highestPrice > (1 - profit_cutoff_pct / 100)
                if min_profit_reached and highest_price > 0:
                    drop_rate = (highest_price - candle_price) / highest_price
                    if drop_rate > drop_threshold:
                        sell_price = candle_price
                        sell_time_str = str(candle['Date'])
                        sell_reason = 'trailing_stop'
                        break
            
            # End of day: 미청산 시 다음날 마지막 캔들 종가로 매도
            if sell_price is None:
                last_candle = next_day_data.iloc[-1]
                sell_price = float(last_candle['Close'])
                sell_time_str = str(last_candle['Date'])
                sell_reason = 'end_of_day'
            
            if sell_price <= 0:
                logger.warning(f"{current_date}: Invalid sell price {sell_price}, skipping")
                continue
            
            # 거래 결과 계산 (전략 1과 동일한 비용 구조)
            gross_profit = (sell_price - buy_price) * (buy_amount / buy_price)
            sell_total = sell_price * (buy_amount / buy_price)
            tax = sell_total * 0.2 / 100
            commission = sell_total * 0.011 / 100
            cost = tax + commission
            net_profit = gross_profit - cost
            
            # 잔고 업데이트
            balance += net_profit
            if net_profit < 0:
                loss_amount += abs(net_profit)
            
            trade = Strategy2Trade(
                buy_time=str(buy_candle['Date']),
                buy_price=buy_price,
                sell_time=sell_time_str,
                sell_price=sell_price,
                buy_amount=buy_amount,
                gross_profit=gross_profit,
                cost=cost,
                profit=net_profit,
                balance_after=balance,
                sell_reason=sell_reason,
                highest_price=highest_price,
                max_profit_pct=max_profit_pct_reached
            )
            trades.append(trade)
            
            logger.info(
                f"[S2 Trade #{len(trades)}] {current_date}→{next_date} | "
                f"BUY@{buy_price:,.0f}({buy_candle['time_str']}) → SELL@{sell_price:,.0f} ({sell_reason}) | "
                f"qty={buy_amount/buy_price:.0f}주 buyAmt={buy_amount:,.0f} | "
                f"gross={gross_profit:+,.0f} cost={cost:,.0f} net={net_profit:+,.0f} | "
                f"bal={balance:,.0f} lossAmt={loss_amount:,.0f} | "
                f"highest={highest_price:,.0f} maxPct={max_profit_pct_reached:.2f}%"
            )
        
        # 매도 사유 통계
        reason_counts = {}
        for t in trades:
            reason_counts[t.sell_reason] = reason_counts.get(t.sell_reason, 0) + 1
        
        logger.info(
            f"Strategy 2 finished | trades={len(trades)}/{len(dates_list)-1}days | "
            f"final_balance={balance:,.0f} | total_loss_amount={loss_amount:,.0f} | "
            f"sell_reasons={reason_counts}"
        )
        return trades
    
    def _calculate_strategy2_performance(self, trades: List[Strategy2Trade]) -> Dict:
        """
        전략 2 성과 지표 계산
        
        @param trades: Strategy2Trade 리스트
        @return: 성과 요약 딕셔너리
        """
        if not trades:
            return {
                'stock_code': self.stock_code,
                'strategy': 'strategy2_trailing_stop',
                'total_profit': 0.0,
                'return_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'mdd': 0.0,
                'total_cost': 0.0,
                'initial_capital': float(self.initial_capital),
                'final_capital': float(self.initial_capital),
                'trading_log': [],
                'equity_curve': [float(self.initial_capital)],
                'sell_reason_stats': {}
            }
        
        winning = [t for t in trades if t.profit > 0]
        losing = [t for t in trades if t.profit <= 0]
        
        total_profit = sum(t.profit for t in trades)
        total_cost = sum(t.cost for t in trades)
        total_wins = sum(t.profit for t in winning)
        total_losses = sum(abs(t.profit) for t in losing)
        
        final_balance = trades[-1].balance_after
        return_rate = (total_profit / self.initial_capital) * 100
        win_rate = (len(winning) / len(trades)) * 100 if trades else 0
        avg_win = total_wins / len(winning) if winning else 0
        avg_loss = total_losses / len(losing) if losing else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # 매도 사유 통계
        sell_reason_stats = {}
        for t in trades:
            sell_reason_stats[t.sell_reason] = sell_reason_stats.get(t.sell_reason, 0) + 1
        
        equity_curve = [float(self.initial_capital)]
        for t in trades:
            equity_curve.append(float(t.balance_after))
        
        mdd = self.calculate_mdd(equity_curve)
        trading_log = [asdict(t) for t in trades]
        
        result = {
            'stock_code': self.stock_code,
            'strategy': 'strategy2_trailing_stop',
            'total_profit': float(total_profit),
            'return_rate': float(return_rate),
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'mdd': float(mdd),
            'total_cost': float(total_cost),
            'initial_capital': float(self.initial_capital),
            'final_capital': float(final_balance),
            'trading_log': trading_log,
            'equity_curve': equity_curve,
            'sell_reason_stats': sell_reason_stats
        }
        
        logger.info(
            f"Strategy 2 results: {self.stock_code} | "
            f"Return={return_rate:+.2f}% | PnL={total_profit:+,.0f} | "
            f"Trades={len(trades)} (W:{len(winning)} L:{len(losing)}) | "
            f"WinRate={win_rate:.1f}% | AvgWin={avg_win:,.0f} AvgLoss={avg_loss:,.0f} | "
            f"PF={profit_factor:.2f} | MDD={mdd:.2f}% | Cost={total_cost:,.0f} | "
            f"Capital: {self.initial_capital:,.0f} → {final_balance:,.0f} | "
            f"Reasons={sell_reason_stats}"
        )
        return result
    
    def _run_legacy_backtest(self, strategy: Dict, prices_dict: Optional[Dict] = None, period: int = 60) -> Dict:
        """
        레거시 백테스팅 실행 (기존 신호 기반 방식)
        
        @param strategy: 전략 설정
        @param prices_dict: Node.js Backend에서 전달받은 주가 데이터
        @param period: 조회 기간
        @return: 백테스팅 결과
        """
        try:
            # 1. 주가 데이터 로드 (Backend 데이터 또는 Yahoo Finance/Mock)
            prices = self.load_price_data(prices_dict=prices_dict, period=period)
            logger.info(f"Loaded {len(prices)} price records")
            
            # 2. 거래 신호 생성
            buy_signals, sell_signals = self.generate_signals(prices, strategy)
            logger.info(f"Buy signals: {len(buy_signals)}, Sell signals: {len(sell_signals)}")
            
            # 3. 주문 실행
            trades_executed = 0
            for idx, row in prices.iterrows():
                date = row['Date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['Date'], 'strftime') else str(row['Date'])
                close_price = float(row['Close'])
                
                if idx in buy_signals:
                    # 현재 잔고로 구매할 수 있는 최대 수량 계산
                    max_quantity = int(self.current_cash / close_price)
                    if max_quantity > 0:
                        self.buy(date, close_price, quantity=max_quantity)
                        trades_executed += 1
                    else:
                        logger.warning(f"Insufficient cash to buy at {date}: available {self.current_cash}, price {close_price}")
                elif idx in sell_signals:
                    self.sell(date, close_price)
                    trades_executed += 1
            
            logger.info(f"Total trades executed: {trades_executed}, Trading log size: {len(self.trading_log)}")
            
            # 4. 결과 계산
            return self.calculate_performance()
        except Exception as e:
            logger.error(f"Backtest error: {str(e)}")
            raise
    
    def generate_signals(self, prices: pd.DataFrame, strategy: Dict) -> Tuple[List[int], List[int]]:
        """
        매매 신호 생성 (구매/판매 시점)
        
        @param strategy 기반:
        - buy_time: 매수 시간 (예: "09:30")
        - sell_time: 매도 시간 (예: "15:50")
        - hold_period: 보유 기간 (일 단위, 기본값: 1)
        
        @return: (buy_signals_list, sell_signals_list) - 인덱스 리스트
        """
        buy_signals = []
        sell_signals = []
        buy_time = strategy.get('buy_time', '09:30')
        sell_time = strategy.get('sell_time', '15:50')
        
        # 데이터 검증 및 디버깅
        logger.info(f"Price data shape: {prices.shape}, columns: {prices.columns.tolist()}")
        if len(prices) > 0:
            logger.info(f"Sample date: {prices.iloc[0]['Date']}, dtype: {prices['Date'].dtype}")
        
        # 간단한 규칙: 매일 매수 시간에 사고, 매도 시간에 팜
        for idx, row in prices.iterrows():
            try:
                date = row['Date']
                # Date가 string이면 변환, datetime이면 그대로 사용
                if isinstance(date, str):
                    date = pd.to_datetime(date)
                
                time_str = date.strftime('%H:%M') if hasattr(date, 'strftime') else str(date)[11:16]
                
                if time_str == buy_time:
                    buy_signals.append(idx)
                    logger.debug(f"Buy signal at idx {idx}, time {time_str}")
                elif time_str == sell_time:
                    sell_signals.append(idx)
                    logger.debug(f"Sell signal at idx {idx}, time {time_str}")
            except Exception as e:
                logger.debug(f"Error parsing date at idx {idx}: {str(e)}")
                continue
        
        # 신호가 없으면 기본값 설정 (매일 매수/매도)
        # Fallback: 매 N개 바마다 매수/매도
        if not buy_signals and len(prices) > 1:
            # 처음 30%에서 매수
            buy_signals = list(range(0, max(1, len(prices) // 3)))
            logger.warning(f"No time-based buy signals found. Using fallback: {len(buy_signals)} buy signals")
        
        if not sell_signals and len(prices) > 1:
            # 남은 70% 구간에서 매도
            sell_signals = list(range(max(1, len(prices) // 3), len(prices)))
            logger.warning(f"No time-based sell signals found. Using fallback: {len(sell_signals)} sell signals")
        
        logger.info(f"Generated {len(buy_signals)} buy and {len(sell_signals)} sell signals")
        return buy_signals, sell_signals
    
    def buy(self, date: str, price: float, quantity: int = 1):
        """
        매수 주문 실행
        
        @param date: 거래 날짜
        @param price: 거래 가격
        @param quantity: 수량
        """
        cost = price * quantity
        if self.current_cash >= cost:
            self.current_cash -= cost
            self.positions.append(Position(
                entry_date=date,
                entry_price=price,
                quantity=quantity
            ))
            trade = Trade(
                date=date,
                type='BUY',
                price=price,
                quantity=quantity,
                cost_or_proceeds=cost,
                cash_remaining=self.current_cash
            )
            self.trading_log.append(trade)
            logger.info(f"BUY: {self.stock_code} {quantity}주 @ {price} on {date}, cost: {cost}, cash remaining: {self.current_cash}")
        else:
            logger.warning(f"Insufficient cash to buy: {cost} > {self.current_cash}")
    
    def sell(self, date: str, price: float):
        """
        매도 주문 실행 (FIFO 방식)
        
        @param date: 거래 날짜
        @param price: 거래 가격
        """
        if not self.positions:
            logger.debug(f"No positions to sell on {date}")
            return
        
        position = self.positions.pop(0)  # FIFO
        proceeds = price * position.quantity
        cost = position.entry_price * position.quantity
        profit = proceeds - cost
        profit_rate = (profit / cost * 100) if cost > 0 else 0
        
        self.current_cash += proceeds
        trade = Trade(
            date=date,
            type='SELL',
            price=price,
            quantity=position.quantity,
            cost_or_proceeds=proceeds,
            profit=profit,
            profit_rate=profit_rate,
            cash_remaining=self.current_cash
        )
        self.trading_log.append(trade)
        logger.info(f"SELL: {self.stock_code} {position.quantity}주 @ {price} on {date}, profit: {profit} ({profit_rate:.2f}%), cash remaining: {self.current_cash}")
    
    def calculate_performance(self) -> Dict:
        """
        백테스팅 성과 지표 계산
        
        @return: 수익률, 승률, MDD, Sharpe Ratio 등
        """
        total_trades = len([t for t in self.trading_log if t.type == 'SELL'])
        winning_trades = len([t for t in self.trading_log if t.type == 'SELL' and (t.profit or 0) > 0])
        losing_trades = total_trades - winning_trades
        
        total_profit = sum([(t.profit or 0) for t in self.trading_log if t.type == 'SELL'])
        return_rate = (total_profit / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        winning_trades_list = [t.profit for t in self.trading_log if t.type == 'SELL' and (t.profit or 0) > 0]
        losing_trades_list = [t.profit for t in self.trading_log if t.type == 'SELL' and (t.profit or 0) <= 0]
        
        avg_win = sum(winning_trades_list) / len(winning_trades_list) if winning_trades_list else 0
        avg_loss = abs(sum(losing_trades_list)) / len(losing_trades_list) if losing_trades_list else 0
        
        # MDD (최대낙률) 계산
        equity_curve = self.calculate_equity_curve()
        mdd = self.calculate_mdd(equity_curve)
        
        # 최종 자산 계산
        final_capital = self.current_cash + sum([p.entry_price * p.quantity for p in self.positions])
        
        result = {
            'stock_code': self.stock_code,
            'total_profit': float(total_profit),
            'return_rate': float(return_rate),
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(avg_win / avg_loss) if avg_loss > 0 else 0,
            'mdd': float(mdd),
            'initial_capital': float(self.initial_capital),
            'final_capital': float(final_capital),
            'trading_log': [asdict(t) for t in self.trading_log],
            'equity_curve': equity_curve
        }
        
        logger.info(f"Backtest completed: {self.stock_code}, Return: {return_rate:.2f}%, Win Rate: {win_rate:.2f}%, MDD: {mdd:.2f}%")
        return result
    
    def calculate_equity_curve(self) -> List[float]:
        """자산 추이 계산"""
        equity = [self.initial_capital]
        for trade in self.trading_log:
            equity.append(trade.cash_remaining)
        return equity
    
    def calculate_mdd(self, equity_curve: List[float]) -> float:
        """Maximum Drawdown 계산 (%)"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        peak = equity_curve[0]
        mdd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100 if peak > 0 else 0
            if dd > mdd:
                mdd = dd
        return mdd

    @staticmethod
    def export_trades_csv(trading_log: List[Dict], strategy_type: str = '') -> str:
        """
        매매 내역을 CSV 문자열로 변환
        
        전략 1 (Strategy1Trade) 필드:
          buy_time, buy_price, sell_time, sell_price, buy_amount,
          gross_profit, cost, profit, balance_after
        
        전략 2 (Strategy2Trade) 추가 필드:
          sell_reason, highest_price, max_profit_pct
        
        @param trading_log: asdict()된 거래 기록 리스트
        @param strategy_type: 전략 유형 ('strategy1_fixed_time' 또는 'strategy2_trailing_stop')
        @return: CSV 문자열 (UTF-8 BOM 포함)
        """
        import io
        import csv
        
        if not trading_log:
            return '\ufeff거래 내역이 없습니다.\n'
        
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM (Excel 한글 호환)
        
        # 전략 2 여부 판단: sell_reason 필드가 있으면 전략 2
        is_strategy2 = (
            strategy_type == 'strategy2_trailing_stop' or
            any('sell_reason' in t for t in trading_log)
        )
        
        # CSV 헤더 정의
        if is_strategy2:
            headers = [
                '번호', '매수일시', '매수가', '매도일시', '매도가',
                '투입금액', '매매차익', '비용(세금+수수료)', '순수익',
                '거래후잔고', '매도사유', '최고가', '최대수익률(%)'
            ]
        else:
            headers = [
                '번호', '매수일시', '매수가', '매도일시', '매도가',
                '투입금액', '매매차익', '비용(세금+수수료)', '순수익',
                '거래후잔고'
            ]
        
        writer = csv.writer(output)
        writer.writerow(headers)
        
        for idx, trade in enumerate(trading_log, 1):
            row = [
                idx,
                trade.get('buy_time', ''),
                trade.get('buy_price', ''),
                trade.get('sell_time', ''),
                trade.get('sell_price', ''),
                round(trade.get('buy_amount', 0), 0),
                round(trade.get('gross_profit', 0), 0),
                round(trade.get('cost', 0), 0),
                round(trade.get('profit', 0), 0),
                round(trade.get('balance_after', 0), 0),
            ]
            if is_strategy2:
                sell_reason_map = {
                    'trailing_stop': '트레일링스탑',
                    'loss_cutoff': '손절',
                    'end_of_day': '장마감매도'
                }
                reason = trade.get('sell_reason', '')
                row.extend([
                    sell_reason_map.get(reason, reason),
                    trade.get('highest_price', ''),
                    round(trade.get('max_profit_pct', 0), 2),
                ])
            writer.writerow(row)
        
        return output.getvalue()


# ==================== 실행 인터페이스 ====================
if __name__ == '__main__':
    """
    Node.js Backend에서 호출되는 진입점
    
    호출 방식:
    python py_backtest/backtest_engine.py '{"stock_code":"005930","strategy":{...},"period":60,"initial_capital":10000000}'
    """
    try:
        # 1. 입력 데이터 파싱
        if len(sys.argv) < 2:
            raise ValueError("Usage: python backtest_engine.py '<json_input>'")
        
        input_json = sys.argv[1]
        input_data = json.loads(input_json)
        
        # 필수 파라미터 추출
        stock_code = input_data.get('stock_code')
        strategy = input_data.get('strategy', {})
        period = input_data.get('period', 60)  # 기본값: 60일
        initial_capital = input_data.get('initial_capital', 10000000)  # 기본값: 1천만원
        
        if not stock_code:
            raise ValueError("stock_code is required")
        
        # strategy에 type이 없으면 buy_time/sell_time이 있을 때 daily_trading으로 자동 설정
        if 'type' not in strategy and 'signal_type' not in strategy:
            if 'buy_time' in strategy and 'sell_time' in strategy:
                strategy['type'] = 'daily_trading'
        
        logger.info(f"Backtest started: {stock_code}, Strategy: {strategy.get('type', 'legacy')}, Period: {period}d, Capital: {initial_capital}")
        
        # 2. BacktestEngine 초기화
        engine = BacktestEngine(stock_code, initial_capital)
        
        # 3. Yahoo Finance에서 데이터 수집 & 백테스팅 실행
        result = engine.run_backtest(strategy, period=period)
        
        # 4. 결과를 JSON으로 출력 (stdout으로 Backend에 전달)
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        # 오류 발생 시 구조화된 오류 메시지 반환
        error_response = {
            "status": "error",
            "stock_code": input_data.get('stock_code', 'unknown') if 'input_data' in locals() else 'unknown',
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        print(json.dumps(error_response, indent=2))
        logger.error(f"Backtest failed: {str(e)}")
        sys.exit(1)
