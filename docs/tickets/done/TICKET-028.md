# TICKET-028: 백테스트 결과 다운로드 엔드포인트 404 에러 버그 수정

**상태**: TODO  
**우선순위**: HIGH  
**발급일**: 2026-02-08  
**에이전트**: 버그 디버깅 담당자  
**버그 분류**: 프론트엔드 코드 버그  
**선행 조건**: TICKET-027 배포 완료  

---

## 버그 설명

### 증상
프론트엔드에서 백테스팅을 진행하고 "결과 다운로드" 버튼을 클릭하면 다음 에러 발생:

```json
{
  "error": "Not Found",
  "message": "GET /api/results/bt-2026-02-08-714/download not found",
  "available_endpoints": [
    "GET /api/health",
    "POST /api/stocks/mode",
    "POST /api/stocks/specific/add",
    "GET /api/stocks/specific",
    "DELETE /api/stocks/specific/:code",
    "POST /api/backtest/start",
    "GET /api/backtest/progress",
    "GET /api/backtest/result/:id"
  ]
}
```

### 근본 원인
1. **프론트엔드가 잘못된 엔드포인트 호출**
   - 호출 중인 엔드포인트: `GET /api/results/bt-{id}/download`
   - 실제 백엔드 엔드포인트: `GET /api/backtest/result/:id`
   
2. **엔드포인트 불일치**
   - TICKET-023 또는 TICKET-026에서 백엔드 API 이름이 변경되었으나, 프론트엔드 코드가 업데이트되지 않음
   - 프론트엔드의 다운로드 기능도 미구현 (백엔드는 한 번의 GET 요청으로 데이터 조회, 다운로드는 별도 처리 필요)

---

## 수정 요구사항

### 1. 엔드포인트 수정
프론트엔드에서 결과 반환 시 사용할 엔드포인트 확인:
- `GET /api/backtest/result/:id` - 현재 백엔드 엔드포인트
- 데이터 형식 및 응답 구조 검증

### 2. 프론트엔드 코드 수정
**파일**: `frontend/pages/specific-stock-selection.html`

#### 수정 내용
- 결과 다운로드 버튼 클릭 이벤트 핸들러 검토
- 올바른 엔드포인트(`/api/backtest/result/:id`)로 요청하도록 수정
- 응답 데이터를 파일로 다운로드하는 로직 구현
  - JSON → CSV 변환 (선택사항)
  - 브라우저 다운로드 트리거

### 3. 테스트
- 프론트엔드에서 백테스트 결과 다운로드 버튼 클릭 시 정상 작동 확인
- 다운로드된 파일 데이터 무결성 검증

---

## 수용 기준

- ✅ 프론트엔드 코드에서 올바른 백엔드 엔드포인트 호출
- ✅ 결과 다운로드 기능 정상 작동 (404 에러 없음)
- ✅ 다운로드 파일이 백테스트 결과를 정확하게 포함
- ✅ 테스트 환경에서 검증 완료

---

## 담당 범위

- 프론트엔드 UI/로직 수정: **버그 디버깅 담당자**
- 백엔드 엔드포인트: **변경 없음** (이미 구현됨)
- 통합 테스트: 후속 테스트 에이전트

---

## 후속 조치

본 티켓 완료 후:
1. TICKET-029: 백테스트 결과 다운로드 기능 재테스트
2. 필요시 배포 버전 업데이트 (2.0.2)
