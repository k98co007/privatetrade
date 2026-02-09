"""
Python Worker Server - Node.js와의 인터페이스
역할: stdin에서 JSON 데이터 수신 → 백테스팅 실행 → JSON 결과 출력
"""

import json
import sys
import logging
from typing import Dict, Any
from backtest_engine import BacktestEngine
from performance_calculator import PerformanceCalculator
from data_cache import get_cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PythonWorkerServer:
    """
    Python Worker Server
    - Node.js 프로세스와의 JSON 기반 통신
    - 백테스팅 엔진 호출 및 결과 반환
    """
    
    def __init__(self):
        """서버 초기화"""
        self.engine = None
        self.calculator = None
        
        # 데이터 캐시 초기화 (SRS NFR-301: 일일 1회 수집)
        self.cache = get_cache()
        self.cache.cleanup_old_cache(keep_days=3)  # 3일 이전 캐시 정리
        
        logger.info(f"Python Worker Server initialized (cache stats: {self.cache.get_stats()})")
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        요청 처리 및 응답 생성
        
        @param request: {
            "stock_code": "005930",
            "strategy": {"buy_time": "09:30", "sell_time": "15:50"},
            "initial_capital": 10000000,
            "start_date": "2025-12-01",
            "end_date": "2026-01-31"
        }
        @return: 백테스팅 결과 JSON
        """
        try:
            # 디버깅: 요청 필드 확인
            logger.info(f"Received request keys: {list(request.keys())}")
            
            stock_code = request.get('stock_code')
            strategy = request.get('strategy', {})
            prices = request.get('prices')  # None if not provided
            initial_capital = request.get('initial_capital', 10000000)
            start_date = request.get('start_date')
            end_date = request.get('end_date')
            
            # strategy에 type이 없으면 buy_time/sell_time이 있을 때 daily_trading으로 자동 설정
            if 'type' not in strategy and 'signal_type' not in strategy:
                if 'buy_time' in strategy and 'sell_time' in strategy:
                    strategy['type'] = 'daily_trading'
                    logger.info(f"Auto-detected strategy type: daily_trading (buy_time/sell_time present)")
            
            # start_date/end_date로부터 period(일 수) 계산
            period = 60  # 기본값
            if start_date and end_date:
                from datetime import datetime as dt
                try:
                    d_start = dt.strptime(start_date, '%Y-%m-%d')
                    d_end = dt.strptime(end_date, '%Y-%m-%d')
                    period = max((d_end - d_start).days, 1)
                    logger.info(f"Calculated period from dates: {period} days ({start_date} ~ {end_date})")
                except ValueError:
                    logger.warning(f"Invalid date format: start={start_date}, end={end_date}. Using default period=60")
            
            logger.info(
                f"Processing backtest | stock={stock_code} | capital={initial_capital:,.0f} | "
                f"period={period}d ({start_date}~{end_date}) | "
                f"strategy={json.dumps(strategy, ensure_ascii=False)}"
            )
            
            # BacktestEngine 인스턴스 생성
            self.engine = BacktestEngine(stock_code, initial_capital)
            
            # 백테스팅 실행 (prices가 없으면 Yahoo Finance에서 직접 조회)
            result = self.engine.run_backtest(strategy, prices, period=period)
            
            # PerformanceCalculator로 추가 지표 계산
            self.calculator = PerformanceCalculator()
            additional_metrics = self.calculator.calculate_all_metrics(
                result.get('equity_curve', []),
                result.get('trading_log', []),
                initial_capital
            )
            
            # 결과에 추가 지표 합병
            result['metrics'] = additional_metrics
            
            # 캐시 통계 추가
            result['cache_stats'] = self.cache.get_stats()
            
            return {
                'status': 'success',
                'data': result,
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'data': None,
                'error': str(e)
            }
    
    def run(self):
        """
        메인 루프: stdin에서 JSON 읽기 → 처리 → stdout으로 JSON 출력
        """
        logger.info("Python Worker Server started, waiting for requests on stdin...")
        
        try:
            for line in sys.stdin:
                try:
                    # JSON 요청 파싱
                    request = json.loads(line.strip())
                    
                    # 요청 처리
                    response = self.process_request(request)
                    
                    # JSON 응답 출력
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {str(e)}")
                    print(json.dumps({
                        'status': 'error',
                        'data': None,
                        'error': f'Invalid JSON: {str(e)}'
                    }))
                    sys.stdout.flush()
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                    print(json.dumps({
                        'status': 'error',
                        'data': None,
                        'error': str(e)
                    }))
                    sys.stdout.flush()
        
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
            sys.exit(1)


def main():
    """진입점"""
    server = PythonWorkerServer()
    server.run()


if __name__ == '__main__':
    main()
