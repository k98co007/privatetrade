"""
PerformanceCalculator - 성과 지표 계산기
역할: 백테스팅 결과의 다양한 성과 지표 계산 및 분석
"""

import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    성과 지표 계산 클래스
    - 수익률, 승률, MDD, Sharpe Ratio, Sortino Ratio 등
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        @param risk_free_rate: 무위험 이자율 (연 기준, 기본값: 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(self, 
                              equity_curve: List[float],
                              trades: List[Dict],
                              initial_capital: float,
                              trading_days: int = 252) -> Dict:
        """
        모든 성과 지표 계산
        
        @param equity_curve: 자산 추이
        @param trades: 거래 로그
        @param initial_capital: 초기 자본금
        @param trading_days: 연간 거래일
        @return: 전체 성과 지표
        """
        metrics = {}
        
        # 기본 지표
        metrics['total_return'] = self.calculate_total_return(equity_curve[-1], initial_capital)
        metrics['annual_return'] = self.calculate_annual_return(
            equity_curve[-1], 
            initial_capital, 
            len(equity_curve)
        )
        
        # 리스크 지표
        metrics['volatility'] = self.calculate_volatility(equity_curve)
        metrics['annual_volatility'] = metrics['volatility'] * np.sqrt(trading_days)
        metrics['mdd'] = self.calculate_mdd(equity_curve)
        
        # 수익성 지표
        metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(equity_curve, self.risk_free_rate)
        metrics['sortino_ratio'] = self.calculate_sortino_ratio(equity_curve, self.risk_free_rate)
        metrics['calmar_ratio'] = self.calculate_calmar_ratio(equity_curve, len(equity_curve))
        
        # 거래 지표
        closing_trades = [t for t in trades if t.get('type') == 'SELL']
        if closing_trades:
            metrics['win_rate'] = self.calculate_win_rate(closing_trades)
            metrics['profit_factor'] = self.calculate_profit_factor(closing_trades)
            metrics['avg_win'] = self.calculate_average_win(closing_trades)
            metrics['avg_loss'] = self.calculate_average_loss(closing_trades)
            metrics['expectancy'] = self.calculate_expectancy(closing_trades)
        
        logger.info(f"Calculated metrics: Return={metrics.get('total_return', 0):.2f}%, "
                   f"Sharpe={metrics.get('sharpe_ratio', 0):.2f}, MDD={metrics.get('mdd', 0):.2f}%")
        
        return metrics
    
    def calculate_total_return(self, final_value: float, initial_value: float) -> float:
        """
        총 수익률 계산 (%)
        
        @return: (종료값 - 초기값) / 초기값 * 100
        """
        if initial_value == 0:
            return 0.0
        return ((final_value - initial_value) / initial_value) * 100
    
    def calculate_annual_return(self, final_value: float, initial_value: float, trading_days: int) -> float:
        """
        연간 수익률 계산 (%)
        
        @param trading_days: 거래일 수
        @return: 연간 수익률
        """
        if initial_value == 0 or trading_days == 0:
            return 0.0
        
        total_return = final_value / initial_value
        years = trading_days / 252  # 년 단위
        annual_return = (total_return ** (1 / years) - 1) * 100 if years > 0 else 0
        return annual_return
    
    def calculate_volatility(self, equity_curve: List[float]) -> float:
        """
        일일 변동성 계산
        
        @return: 표준편차 (일일)
        """
        if len(equity_curve) < 2:
            return 0.0
        
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        volatility = np.std(returns)
        return volatility
    
    def calculate_mdd(self, equity_curve: List[float]) -> float:
        """
        Maximum Drawdown 계산 (%)
        
        @return: MDD 비율
        """
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
    
    def calculate_sharpe_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Sharpe Ratio 계산
        
        Sharpe Ratio = (포트폴리오 수익률 - 무위험률) / 변동성
        
        @param risk_free_rate: 연간 무위험 이자율
        @return: Sharpe Ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        avg_return = np.mean(returns) * 252  # 연환산
        volatility = np.std(returns) * np.sqrt(252)
        
        if volatility == 0:
            return 0.0
        
        sharpe = (avg_return - risk_free_rate) / volatility
        return sharpe
    
    def calculate_sortino_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Sortino Ratio 계산 (하방 위험도만 고려)
        
        @return: Sortino Ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        avg_return = np.mean(returns) * 252
        
        # 음수 수익만 고려
        downside_returns = returns[returns < 0]
        downside_volatility = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        if downside_volatility == 0:
            return 0.0
        
        sortino = (avg_return - risk_free_rate) / downside_volatility
        return sortino
    
    def calculate_calmar_ratio(self, equity_curve: List[float], trading_days: int) -> float:
        """
        Calmar Ratio 계산
        
        Calmar = 연간 수익률 / MDD
        
        @return: Calmar Ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        annual_return = self.calculate_annual_return(equity_curve[-1], equity_curve[0], trading_days)
        mdd = self.calculate_mdd(equity_curve)
        
        if mdd == 0 or mdd < 0.01:
            return 0.0
        
        calmar = annual_return / mdd
        return calmar
    
    def calculate_win_rate(self, closing_trades: List[Dict]) -> float:
        """
        승률 계산 (%)
        
        @param closing_trades: SELL 거래 로그
        @return: 승률 비율
        """
        if not closing_trades:
            return 0.0
        
        winning = len([t for t in closing_trades if (t.get('profit', 0) or 0) > 0])
        return (winning / len(closing_trades)) * 100
    
    def calculate_profit_factor(self, closing_trades: List[Dict]) -> float:
        """
        이익 지수 계산
        
        Profit Factor = 총 이익 / 총 손실
        
        @return: Profit Factor
        """
        winning_trades = [t for t in closing_trades if (t.get('profit', 0) or 0) > 0]
        losing_trades = [t for t in closing_trades if (t.get('profit', 0) or 0) <= 0]
        
        total_profit = sum([t.get('profit', 0) or 0 for t in winning_trades])
        total_loss = abs(sum([t.get('profit', 0) or 0 for t in losing_trades]))
        
        if total_loss == 0:
            return 0.0
        
        return total_profit / total_loss if total_profit > 0 else 0.0
    
    def calculate_average_win(self, closing_trades: List[Dict]) -> float:
        """평균 수익 계산"""
        winning_trades = [t for t in closing_trades if (t.get('profit', 0) or 0) > 0]
        if not winning_trades:
            return 0.0
        return sum([t.get('profit', 0) or 0 for t in winning_trades]) / len(winning_trades)
    
    def calculate_average_loss(self, closing_trades: List[Dict]) -> float:
        """평균 손실 계산"""
        losing_trades = [t for t in closing_trades if (t.get('profit', 0) or 0) <= 0]
        if not losing_trades:
            return 0.0
        return sum([abs(t.get('profit', 0) or 0) for t in losing_trades]) / len(losing_trades)
    
    def calculate_expectancy(self, closing_trades: List[Dict]) -> float:
        """
        기댓값 계산 (거래당 평균 수익)
        
        Expectancy = (win% * avg_win) - (loss% * avg_loss)
        
        @return: 거래당 기댓값
        """
        if not closing_trades:
            return 0.0
        
        win_rate = self.calculate_win_rate(closing_trades) / 100
        loss_rate = 1 - win_rate
        avg_win = self.calculate_average_win(closing_trades)
        avg_loss = self.calculate_average_loss(closing_trades)
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        return expectancy
