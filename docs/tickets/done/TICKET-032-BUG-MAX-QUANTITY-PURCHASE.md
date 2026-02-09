# TICKET-032: 백테스팅 엔진 최대 수량 구매 버그 수정

**상태**: `todo`  
**등록일**: 2026-02-08  
**담당자**: 개발 디버깅 담당자  
**버그 분류**: 코드(backtest_engine.py)  

## 버그 설명

### 문제 상황
- 초기 자본금: 1,000만원
- 주식 가격: 10,000원
- **예상 동작**: 최대 1,000주 구매 가능
- **실제 동작**: 1주만 구매됨

### 근본 원인
[py_backtest/backtest_engine.py](py_backtest/backtest_engine.py#L104) 라인에서:
```python
if idx in buy_signals:
    self.buy(date, close_price, quantity=strategy.get('quantity', 1))
```

현재 잔고로 구매할 수 있는 **최대 수량을 계산하지 않고**, 고정된 수량(기본값: 1주)만 구매하고 있음.

### 수정 필요 사항
1. `buy()` 메서드 호출 시 현재 잔고(self.current_cash)로 구매할 수 있는 최대 수량 계산
2. 수식: `max_quantity = floor(self.current_cash / close_price)`
3. 계산된 최대 수량으로 매수 실행

## 수용 기준
- [ ] 코드 수정 완료
- [ ] 1,000만원 초기자본, 10,000원 주가 기준 최대 1,000주 구매 확인
- [ ] 기존 테스트 케이스 통과
- [ ] 신규 테스트 케이스 작성 및 통과

## 참고 자료
- [py_backtest/backtest_engine.py](py_backtest/backtest_engine.py)
- [test_backtest_fix.py](test_backtest_fix.py)
