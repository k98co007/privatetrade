# TICKET-025: 백테스트 결과 표시 기능 테스트 환경 구성

**상태**: TODO  
**우선순위**: HIGH  
**발급일**: 2026-02-08  
**에이전트**: LLD 테스트 환경 담당자  
**관련 티켓**: TICKET-023 (선행 완료)  

---

## 배경

TICKET-023에서 백테스트 결과 표시 기능이 완료되었습니다. 이 기능을 테스트하기 위한 환경을 구성해야 합니다.

---

## 요구사항

### 1. 테스트 환경 구성

#### 1.1 Backend Mock API 설정
현재 백엔드는 mock 데이터를 반환하고 있으므로:

**확인 사항**:
- ✓ POST /api/backtest/start
  - 요청: `{ strategy, start_date, end_date, initial_capital, stock_mode }`
  - 응답: `{ success: true, backtest_id: "bt-2026-02-08-XXX", status: "running" }`
- ✓ GET /api/backtest/progress?id=XXX
  - 응답: `{ backtest_id, status: "running|completed", progress_percent: 0-100 }`
  - **동작**: 각 호출마다 progress_percent를 10% 증가 (누적)
- ✓ GET /api/backtest/result/{id}
  - 응답: 다음 데이터 구조로 안정적 반환 필수:
    ```javascript
    {
      backtest_id: "bt-2026-02-08-123",
      status: "completed",
      performance: {
        total_return: "45.32%",
        sharpe_ratio: 1.85,
        max_drawdown: "-12.5%",
        total_trades: 247,
        win_rate: "56.8%"
      },
      results_file: "/api/results/xxx.csv",
      completed_at: "2026-02-08T22:02:00Z"
    }
    ```

**수정 필요 내용**:
- progress 폴링 중 progress_percent가 매번 증가하도록 수정 (현재 random)
- 최소 10초 동안 진행 상황을 단계별로 시뮬레이션

**파일**: `backend/server.js` (라인 220-245)

#### 1.2 Frontend 테스트 환경
**브라우저 환경**:
- Chrome/Chromium (최신 버전)
- Firefox (최신 버전)
- Safari (선택사항)

**개발자 도구 설정**:
- Network throttling: Fast 3G 또는 정상 속도
- Console: 에러, 경고 메시지 모니터링
- Performance: 진행 바 애니메이션 성능 확인

#### 1.3 테스트 데이터 준비
**특정 종목 선택 시나리오**:
- 테스트값: 삼성전자(005930), SK하이닉스(000660), 셀트리온(068270) 3개 선택
- 전략: MA20_50 (기본값)
- 기간: 2024-01-01 ~ 2025-12-31

**예상 결과 데이터**:
- 총 수익률: 45.32% (양수)
- 샤프 지수: 1.85
- 최대 손실률: -12.5% (음수)
- 거래 횟수: 247회
- 승률: 56.8%

#### 1.4 테스트 환경 문서화
**체크리스트 작성**:
```
[ ] Backend 서버 실행 확인
  [ ] 포트 8000에서 리스닝 중
  [ ] /api/health 정상
  [ ] Mock 데이터 반환 확인
[ ] Frontend 웹페이지 로드 확인
  [ ] http://localhost:8000/pages/specific-stock-selection.html 접근 가능
  [ ] 모든 요소 렌더링됨
[ ] Network 통신 확인
  [ ] 개발자 도구 Network 탭에서 API 호출 트레이싱 가능
  [ ] 요청/응답 데이터 확인 가능
[ ] Console 에러 확인
  [ ] 콘솔에 에러 메시지 없음
  [ ] 경고 레벨 로그만 표시
```

### 2. Mock API 개선 (선택사항이 아닌 필수)

**문제점**: 현재 progress 폴링이 불안정함
- 매 요청마다 random 값 반환 (낮아질 수도, 높아질 수도 있음)
- 진짜 진행 상황처럼 보이지 않음

**수정 방안**:
```javascript
// backend/server.js의 GET /api/backtest/progress 수정
// 각 backtest_id별로 진행 상황을 메모리에 유지
const backtestProgress = {}; // { backtestId: { percent, status, startTime } }

app.get('/api/backtest/progress', (req, res) => {
  const { id } = req.query;
  
  if (!backtestProgress[id]) {
    backtestProgress[id] = { percent: 0, status: 'running', startTime: Date.now() };
  }
  
  const progress = backtestProgress[id];
  const elapsed = (Date.now() - progress.startTime) / 1000; // 초 단위
  
  // 10초마다 10% 증가
  progress.percent = Math.min(eligible(elapsed / 10) * 10, 100);
  
  if (progress.percent >= 100) {
    progress.status = 'completed';
  }
  
  res.json({
    backtest_id: id,
    status: progress.status,
    progress_percent: progress.percent
  });
});
```

### 3. 환경 체크리스트

**구성 완료 확인**: 아래 모든 항목이 ✓ 완료되어야 함

#### Server & API
- [ ] Backend 서버 정상 작동
- [ ] /api/health 정상 (200 OK)
- [ ] /api/backtest/start 정상 (backtest_id 반환)
- [ ] /api/backtest/progress 정상 (누적 진행률 반환)
- [ ] /api/backtest/result/{id} 정상 (성과 지표 5개 반환)

#### Frontend & Browser
- [ ] 웹페이지 로드 성공
- [ ] 모든 HTML 요소 렌더링됨
- [ ] JavaScript 에러 없음 (개발자 도구 Console)
- [ ] CSS 스타일 정상 렌더링
- [ ] 브라우저 호환성 확인 (Chrome, Firefox)

#### Network & Performance
- [ ] 네트워크 통신 정상 (개발자 도구 Network 탭)
- [ ] 응답 시간 < 1초 (진행 폴링)
- [ ] 진행 바 애니메이션 부드러움
- [ ] 메모리 누수 없음 (DevTools Performance)

#### Test Data & Scenarios
- [ ] Mock 데이터 준비 (5개 성과 지표)
- [ ] 특정 종목 선택 테스트 데이터 준비
- [ ] 에러 시나리오 시뮬레이션 가능한 환경 구성

---

## 제출 요구사항

1. **환경 구성 보고서**: `docs/test/lld/test-environment-setup-backtest.md`
   - 서버/브라우저/네트워크 설정 내용
   - 체크리스트 (모두 ✓ 표시)

2. **Mock API 수정사항**: `backend/server.js` 업데이트
   - 진행 상황 누적 로직 적용
   - 안정적인 데이터 반환 확인

3. **스크린샷나 로그**:
   - 서버 시작 로그
   - 개발자 도구 Network 탭 스크린샷 (API 호출)
   - Console 에러 없음 확인 스크린샷

---

## 완료 기준

- ✓ Backend 서버 정상 작동
- ✓ 모든 API 엔드포인트 정상 응답
- ✓ Frontend 웹페이지 로드 및 렌더링 정상
- ✓ 환경 체크리스트 모두 ✓ 완료
- ✓ TICKET-024 테스트 케이스 실행 가능한 수준

---

## 다음 단계

1. TICKET-024: LLD 테스트 케이스 작성 (병렬 진행)
2. TICKET-026: 테스트 수행 (TICKET-024, 025 완료 후)
3. TICKET-027: 배포 (TICKET-026 완료 후)
