"""
SignalGenerator - 매매 신호 생성기
역할: 주가 데이터 기반 매매 신호 생성 (볼린저밴드, 이동평균 등)
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    매매 신호 생성 클래스
    - 기술적 분석 지표 기반 매매 신호
    - 볼린저밴드, 이동평균, RSI 등 지원
    """
    
    def __init__(self):
        """SignalGenerator 초기화"""
        pass
    
    def generate_signals(self, prices: pd.DataFrame, strategy: Dict) -> Tuple[List[int], List[int]]:
        """
        매매 신호 생성
        
        @param prices: OHLCV 데이터프레임
        @param strategy: 전략 설정
        @return: (buy_signals, sell_signals)
        """
        signal_type = strategy.get('signal_type', 'simple_time')
        
        if signal_type == 'simple_time':
            return self._simple_time_based_signals(prices, strategy)
        elif signal_type == 'bollinger_band':
            return self._bollinger_band_signals(prices, strategy)
        elif signal_type == 'moving_average':
            return self._moving_average_signals(prices, strategy)
        else:
            logger.warning(f"Unknown signal type: {signal_type}, using default")
            return self._simple_time_based_signals(prices, strategy)
    
    def _simple_time_based_signals(self, prices: pd.DataFrame, strategy: Dict) -> Tuple[List[int], List[int]]:
        """
        시간 기반 단순 신호
        - 지정된 시간에 매수, 지정된 시간에 매도
        """
        buy_signals = []
        sell_signals = []
        
        buy_time = strategy.get('buy_time', '09:30')
        sell_time = strategy.get('sell_time', '15:50')
        
        for idx, row in prices.iterrows():
            date = row['Date']
            time_str = date.strftime('%H:%M') if hasattr(date, 'strftime') else str(date)[11:16]
            
            if time_str == buy_time:
                buy_signals.append(idx)
            elif time_str == sell_time:
                sell_signals.append(idx)
        
        # 신호 없으면 기본 설정
        if not buy_signals:
            buy_signals = [i for i in range(0, len(prices), max(1, len(prices) // 20))]
        if not sell_signals:
            sell_signals = [i for i in range(1, len(prices), max(1, len(prices) // 20))]
        
        logger.info(f"Simple time signals: {len(buy_signals)} buys, {len(sell_signals)} sells")
        return buy_signals, sell_signals
    
    def _bollinger_band_signals(self, prices: pd.DataFrame, strategy: Dict) -> Tuple[List[int], List[int]]:
        """
        볼린저밴드 기반 신호
        - 가격이 하단 밴드 터치 → 매수
        - 가격이 상단 밴드 터치 → 매도
        """
        buy_signals = []
        sell_signals = []
        
        period = strategy.get('bb_period', 20)
        std_dev = strategy.get('bb_std', 2)
        
        # 이동평균과 표준편차 계산
        prices['MA'] = prices['Close'].rolling(window=period).mean()
        prices['STD'] = prices['Close'].rolling(window=period).std()
        prices['Upper'] = prices['MA'] + (std_dev * prices['STD'])
        prices['Lower'] = prices['MA'] - (std_dev * prices['STD'])
        
        for idx in range(period, len(prices)):
            close = prices.iloc[idx]['Close']
            lower = prices.iloc[idx]['Lower']
            upper = prices.iloc[idx]['Upper']
            
            # 하단 밴드 터치 → 매수
            if close <= lower and not np.isnan(lower):
                buy_signals.append(idx)
            # 상단 밴드 터치 → 매도
            elif close >= upper and not np.isnan(upper):
                sell_signals.append(idx)
        
        logger.info(f"Bollinger band signals: {len(buy_signals)} buys, {len(sell_signals)} sells")
        return buy_signals, sell_signals
    
    def _moving_average_signals(self, prices: pd.DataFrame, strategy: Dict) -> Tuple[List[int], List[int]]:
        """
        이동평균 크로스 신호
        - 단기 MA > 장기 MA → 매수
        - 단기 MA < 장기 MA → 매도
        """
        buy_signals = []
        sell_signals = []
        
        short_period = strategy.get('ma_short', 5)
        long_period = strategy.get('ma_long', 20)
        
        prices['MA_Short'] = prices['Close'].rolling(window=short_period).mean()
        prices['MA_Long'] = prices['Close'].rolling(window=long_period).mean()
        
        prev_short = None
        prev_long = None
        
        for idx in range(long_period, len(prices)):
            short_ma = prices.iloc[idx]['MA_Short']
            long_ma = prices.iloc[idx]['MA_Long']
            
            if np.isnan(short_ma) or np.isnan(long_ma):
                continue
            
            # Golden Cross (단기 > 장기) → 매수
            if prev_short is not None and prev_long is not None:
                if prev_short <= prev_long and short_ma > long_ma:
                    buy_signals.append(idx)
                # Death Cross (단기 < 장기) → 매도
                elif prev_short >= prev_long and short_ma < long_ma:
                    sell_signals.append(idx)
            
            prev_short = short_ma
            prev_long = long_ma
        
        logger.info(f"Moving average signals: {len(buy_signals)} buys, {len(sell_signals)} sells")
        return buy_signals, sell_signals
    
    def calculate_rsi(self, prices: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        RSI (Relative Strength Index) 계산
        
        @param prices: Close 가격
        @param period: 기간 (기본값: 14)
        @return: RSI 딕셔너리
        """
        delta = prices['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence) 계산
        
        @return: (MACD, Signal Line, Histogram)
        """
        ema_12 = prices['Close'].ewm(span=12).mean()
        ema_26 = prices['Close'].ewm(span=26).mean()
        
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        
        return macd, signal, histogram
