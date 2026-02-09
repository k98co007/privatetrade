# LLD 테스트 문서 - 특정 종목 선택 기능 (v2.0)
**작성일**: 2026년 2월 8일  
**기반**: LLD 2.0  
**버전**: 2.0  
**테스트 커버리지**: 80% 이상 목표  

---

## 테스트 케이스 총 51개

### 섹션 1: API - POST /api/stocks/mode (5개 TC)

#### TC-API-001: 정상 - 모드를 'all'로 전환
- **전제조건**: 현재 모드 = 'specific'
- **입력**: `POST /api/stocks/mode` with `{ "mode": "all" }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "current_mode": "all" }`
  - 특정 종목 리스트 자동 초기화
- **점검**: DB에서 stock_mode = 'all' 확인

#### TC-API-002: 정상 - 모드를 'filtered'로 전환
- **전제조건**: 현재 모드 = 'all'
- **입력**: `POST /api/stocks/mode` with `{ "mode": "filtered" }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "current_mode": "filtered" }`
- **점검**: 블랙/화이트리스트 기반 필터링 준비됨

#### TC-API-003: 정상 - 모드를 'specific'으로 전환
- **전제조건**: 현재 모드 = 'filtered'
- **입력**: `POST /api/stocks/mode` with `{ "mode": "specific" }`
- **기대 결과**: HTTP 200 OK, `{ "success": true, "current_mode": "specific" }`
- **점검**: UI에서 특정 종목 선택 섹션 활성화

#### TC-API-004: 오류 - 잘못된 모드 값
- **전제조건**: 현재 모드 = 'all'
- **입력**: `POST /api/stocks/mode` with `{ "mode": "invalid_mode" }`
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "Invalid stock_mode. Must be: all, filtered, or specific" }`
- **점검**: 모드 변경 없음, 이전 상태 유지

#### TC-API-005: 오류 - 필수 필드 누락
- **전제조건**: 현재 모드 = 'all'
- **입력**: `POST /api/stocks/mode` with `{}`  (mode 필드 없음)
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "mode field is required" }`
- **점검**: 에러 로그에 기록됨

---

### 섹션 2: API - POST /api/stocks/specific/add (12개 TC)

#### TC-API-006: 정상 - 1개 종목 추가
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 0
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["005930"] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 1, "selected_stocks": ["005930"] }`
- **점검**: DB에 저장, UI 목록에 표시

#### TC-API-007: 정상 - 3개 종목 동시 추가
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 0
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["005930", "000660", "068270"] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 3, ... }`
- **점검**: 모두 DB에 저장됨

#### TC-API-008: 정상 - 중복 코드 자동 제거
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 0
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["005930", "005930", "000660"] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 2, "selected_stocks": ["005930", "000660"] }`
- **점검**: 중복 제거 확인

#### TC-API-009: 오류 - 빈 배열
- **전제조건**: 모드 = 'specific'
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": [] }`
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "codes must be a non-empty array" }`
- **점검**: 종목이 추가되지 않음

#### TC-API-010: 오류 - codes 필드가 배열이 아님
- **전제조건**: 모드 = 'specific'
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": "005930" }`  (문자열)
- **기대 결과**: HTTP 400 Bad Request
- **점검**: 타입 검증 확인

#### TC-API-011: 오류 - 최대값 초과 (101개)
- **전제조건**: 모드 = 'specific'
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": [100개 종목 코드 + 1개] }`
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "Maximum 100 stocks allowed" }`
- **점검**: 어떤 종목도 추가되지 않음

#### TC-API-012: 오류 - 잘못된 형식 (4자리 코드)
- **전제조건**: 모드 = 'specific'
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["0059"] }`  (6자리 아님)
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "Invalid stock codes: 0059" }`
- **점검**: 종목 추가 불가

#### TC-API-013: 오류 - 사문자 포함
- **전제조건**: 모드 = 'specific'
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["00593A"] }`  (A 포함)
- **기대 결과**: HTTP 400 Bad Request, 형식 오류
- **점검**: 숫자만 허용

#### TC-API-014: 정상 - 100개 정확히 추가
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 0
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": [100개 정확히] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 100, ... }`
- **점검**: DB에 모두 저장됨

#### TC-API-015: 정상 - 기존 선택에 추가 (5개 + 3개 = 8개)
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 5
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["신규 3개"] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 8, ... }`
- **점검**: 기존과 신규 합산됨

#### TC-API-016: 오류 - 이미 선택된 종목 재추가 시도
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930']
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": ["005930", "000660"] }`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 2, "selected_stocks": ["005930", "000660"] }`
- **점검**: 중복된 '005930'은 1번만 저장, '000660' 신규 추가

#### TC-API-017: 오류 - 최대값 초과 (5개 기존 + 96개 신규 = 101개)
- **전제조건**: 모드 = 'specific', 선택 종목 수 = 5
- **입력**: `POST /api/stocks/specific/add` with `{ "codes": [96개 신규] }`
- **기대 결과**: HTTP 400 Bad Request, 최대값 초과 메시지
- **점검**: 기존 5개도 변경 없음

---

### 섹션 3: API - GET /api/stocks/specific (5개 TC)

#### TC-API-018: 정상 - 선택 종목 조회 (3개 선택 상태)
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930', '000660', '068270']
- **입력**: `GET /api/stocks/specific`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "current_mode": "specific", "selected_count": 3, "selected_stocks": ["005930", "000660", "068270"] }`
- **점검**: 전체 필드 확인

#### TC-API-019: 정상 - 선택 종목 없을 때 조회
- **전제조건**: 모드 = 'all', 선택 종목 수 = 0
- **입력**: `GET /api/stocks/specific`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "current_mode": "all", "selected_count": 0, "selected_stocks": [] }`
- **점검**: 0개 반환

#### TC-API-020: 정상 - 100개 종목 조회
- **전제조건**: 모드 = 'specific', 선택 종목 = 100개
- **입력**: `GET /api/stocks/specific`
- **기대 결과**: 
  - HTTP 200 OK
  - Response with all 100 stocks, selected_count = 100
- **점검**: 페이지네이션 불필요 (100개 이하)

#### TC-API-021: 정상 - 모드 'filtered'에서 조회
- **전제조건**: 모드 = 'filtered', 선택 종목은 무시
- **입력**: `GET /api/stocks/specific`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "current_mode": "filtered", "selected_count": 0, "selected_stocks": [] }`
- **점검**: 모드 반영

#### TC-API-022: 정상 - 모드 'all'에서 조회
- **전제조건**: 모드 = 'all'
- **입력**: `GET /api/stocks/specific`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "current_mode": "all", "selected_count": 0, "selected_stocks": [] }`

---

### 섹션 4: API - DELETE /api/stocks/specific/:code (8개 TC)

#### TC-API-023: 정상 - 종목 1개 제거
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930', '000660']
- **입력**: `DELETE /api/stocks/specific/005930`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 1 }`
- **점검**: '005930' 제거, '000660' 남아있음

#### TC-API-024: 정상 - 마지막 종목 제거
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930']
- **입력**: `DELETE /api/stocks/specific/005930`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 0 }`
- **점검**: 모든 종목 제거됨

#### TC-API-025: 오류 - 존재하지 않는 종목 제거 시도
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930']
- **입력**: `DELETE /api/stocks/specific/999999`  (선택되지 않은 종목)
- **기대 결과**: 
  - HTTP 200 OK (멱등성)
  - Response: `{ "success": true, "selected_count": 1 }`  (변경 없음)
- **점검**: 기존 선택 유지

#### TC-API-026: 오류 - 잘못된 형식 코드
- **전제조건**: 모드 = 'specific'
- **입력**: `DELETE /api/stocks/specific/0059`  (4자리)
- **기대 결과**: 
  - HTTP 400 Bad Request
  - Response: `{ "success": false, "error": "Invalid stock code format" }`
- **점검**: 어떤 종목도 제거 안 됨

#### TC-API-027: 오류 - 사문자 포함 코드
- **전제조건**: 모드 = 'specific'
- **입력**: `DELETE /api/stocks/specific/00593A`
- **기대 결과**: HTTP 400 Bad Request

#### TC-API-028: 정상 - 여러 번 제거 (멱등성)
- **전제조건**: 모드 = 'specific', 선택 종목 = ['005930']
- **입력**: `DELETE /api/stocks/specific/005930` x 2회 연속
- **기대 결과**: 
  - 1차: HTTP 200, selected_count = 0
  - 2차: HTTP 200, selected_count = 0 (변경 없음, 멱등성)
- **점검**: 에러 없음

#### TC-API-029: 정상 - 100개 중 1개 제거
- **전제조건**: 모드 = 'specific', 선택 종목 = 100개
- **입력**: `DELETE /api/stocks/specific/[첫번째 코드]`
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "selected_count": 99 }`
- **점검**: 99개 남음

#### TC-API-030: 정상 - 전체 초기화 엔드포인트
- **전제조건**: 모드 = 'specific', 선택 종목 = 5개
- **입력**: `DELETE /api/stocks/specific` (경로에 code 없음)
- **기대 결과**: 
  - HTTP 200 OK
  - Response: `{ "success": true, "message": "All specific stocks cleared" }`
- **점검**: 모든 선택 종목 초기화

---

### 섹션 5: UI 테스트 (10개 TC)

#### TC-UI-031: 정상 - 모드 라디오 버튼 선택
- **전제조건**: 브라우저에서 특정 종목 선택 페이지 오픈
- **입력**: "특정 종목만" 라디오 버튼 클릭
- **기대 결과**:
  - 라디오 버튼 선택됨 (체크 마크)
  - 특정 종목 입력 섹션 표시 (display: block)
  - 문자: "선택된 종목: 0개"
- **점검**: CSS 클래스 'active' 확인

#### TC-UI-032: 정상 - 종목 코드 입력 및 추가
- **전제조건**: 모드 = 'specific', 종목 입력 필드 포커스됨
- **입력**: 종목 코드 '005930' 입력 후 "추가" 버튼 클릭
- **기대 결과**:
  - 목록에 "005930 삼성전자" 표시
  - 카운트 변경: "선택된 종목: 1개"
  - 입력 필드 초기화 (비었음)
- **점검**: API 호출 확인 (F12 네트워크 탭)

#### TC-UI-033: 정상 - 선택된 종목 개별 제거
- **전제조건**: 선택 종목 = ['005930', '000660']
- **입력**: '005930' 옆 "제거" 버튼 클릭
- **기대 결과**:
  - '005930' 항목 사라짐
  - '000660'만 남음
  - 카운트: "선택된 종목: 1개"
- **점검**: DOM 업데이트 확인

#### TC-UI-034: 정상 - 오류 메시지 표시 (빈 입력)
- **전제조건**: 모드 = 'specific', 입력 필드 비어있음
- **입력**: "추가" 버튼 클릭
- **기대 결과**:
  - 오류 메시지: "종목 코드 또는 명을 입력해주세요."
  - 메시지 3초 후 자동 사라짐
- **점검**: 오류 스타일 (background-color: #f8d7da)

#### TC-UI-035: 정상 - 오류 메시지 표시 (중복 종목)
- **전제조건**: 선택 종목 = ['005930']
- **입력**: '005930' 다시 입력 후 "추가" 클릭
- **기대 결과**:
  - 오류 메시지: "이미 추가된 종목입니다: 삼성전자"
- **점검**: 중복 체크 로직 확인

#### TC-UI-036: 정상 - 전체 초기화 버튼
- **전제조건**: 선택 종목 = ['005930', '000660', '068270']
- **입력**: "전체 초기화" 버튼 클릭 → 확인 대화상자 "확인" 클릭
- **기대 결과**:
  - 모든 선택 종목 사라짐
  - 카운트: "선택된 종목: 0개"
  - 성공 메시지: "모든 종목이 초기화되었습니다."
- **점검**: confirm() 대화상자 표시됨

#### TC-UI-037: 정상 - 전체 초기화 취소
- **전제조건**: 선택 종목 = ['005930']
- **입력**: "전체 초기화" 버튼 클릭 → 확인 대화상자 "취소" 클릭
- **기대 결과**:
  - 선택 종목 유지: ['005930']
  - 카운트 변경 없음
- **점검**: 초기화 안 됨

#### TC-UI-038: 정상 - 최대값 도달 오류
- **전제조건**: 선택 종목 수 = 100개
- **입력**: 종목 코드 입력 후 "추가" 버튼 클릭
- **기대 결과**:
  - 오류 메시지: "최대 100개까지만 추가할 수 있습니다."
- **점검**: 추가 안 됨

#### TC-UI-039: 정상 - 캐시 초기화 후 UI 상태 유지
- **전제조건**: 선택 종목 = ['005930', '000660'], 페이지 새로 고침
- **입력**: F5 또는 Ctrl+R로 새로 고침
- **기대 결과**:
  - 페이지 강제 리로드 후 선택 종목 유지 (localStorage 또는 DB에서 조회)
  - 목록에 2개 항목 표시
- **점검**: 로컬 스토리지 검증

#### TC-UI-040: 정상 - 백테스팅 시작 버튼 활성화/비활성화
- **전제조건** (활성화): 선택 종목 ≥ 1개, 전략 선택됨
- **입력**: 백테스팅 시작 버튼 클릭
- **기대 결과**: 메시지 "2개 종목에 대한 백테스팅을 시작합니다..."
- **대조** (비활성화): 선택 종목 = 0개일 때
- **기대 결과**: 버튼 비활성화 상태 또는 오류 메시지 표시

---

### 섹션 6: 통합 테스트 (10개 TC)

#### TC-INT-041: 정상 - 전체 플로우 (모드 전환 → 종목 추가 → 백테스팅)
- **시나리오**:
  1. 페이지 오픈 → 기본 모드 = 'all'
  2. "특정 종목만" 선택
  3. ['005930', '000660'] 추가
  4. 전략 선택 (고정시간 매수/매도)
  5. 백테스팅 시작
- **기대 결과**:
  - 모든 API 호출 성공 (4xx/5xx 없음)
  - UI 상태 일관성 유지
  - 백테스팅 진행 메시지 표시
- **점검**: 네트워크 탭에서 모든 요청 200-299 확인

#### TC-INT-042: 정상 - 모드 전환 시 상태 초기화
- **시나리오**:
  1. 모드 = 'specific', 선택 종목 = ['005930']
  2. 모드 'all'로 전환
  3. GET /api/stocks/specific 호출
- **기대 결과**: selected_count = 0 (자동 초기화)

#### TC-INT-043: 정상 - 종목 추가 후 조회 일관성
- **시나리오**:
  1. POST /api/stocks/specific/add ['005930', '000660']
  2. GET /api/stocks/specific
- **기대 결과**: 반환된 리스트와 추가한 리스트 동일

#### TC-INT-044: 정상 - 개별 제거 후 목록 일관성
- **시나리오**:
  1. 선택 종목 = ['005930', '000660', '068270']
  2. DELETE /api/stocks/specific/000660
  3. GET /api/stocks/specific
- **기대 결과**: ['005930', '068270'] 반환 (000660 제외)

#### TC-INT-045: 정상 - 데이터 퍼시스턴스 (DB 저장 확인)
- **시나리오**:
  1. POST /api/stocks/specific/add ['005930']
  2. 데이터베이스 직접 쿼리: SELECT selected_specific_stocks FROM config
- **기대 결과**: JSON 배열 '["005930"]' 저장되어 있음

#### TC-INT-046: 정상 - 100회 추가/제거 반복 안정성
- **시나리오**:
  1. 반복: 종목 추가 → 제거 → 조회 (100회)
- **기대 결과**:
  - 모든 작업 성공
  - 메모리 누수 없음 (메모리 사용량 안정적)
- **점검**: 브라우저 DevTools 메모리 탭

#### TC-INT-047: 정상 - 동시성 (2개 탭에서 동시 추가)
- **시나리오**:
  1. 탭 A: POST /api/stocks/specific/add ['005930']
  2. 탭 B: POST /api/stocks/specific/add ['000660'] (거의 동시)
  3. 양 탭에서 GET /api/stocks/specific
- **기대 결과**:
  - 탭 A: ['005930', '000660'] 또는 ['005930']
  - 탭 B: ['000660', '005930'] 또는 ['000660']
  - (최종 결과는 마지막 쓰기 기준)

#### TC-INT-048: 정상 - 네트워크 지연 시뮬레이션
- **전제조건**: 브라우저 DevTools에서 네트워크 스로틀 = "Fast 3G"
- **시나리오**: 종목 추가 → 조회
- **기대 결과**:
  - 모든 작업 완료 (타임아웃 없음)
  - UI 반응성 유지 (로딩 표시)

#### TC-INT-049: 정상 - 에러 복구 (API 실패 후 재시도)
- **시나리오**:
  1. POST /api/stocks/specific/add ['005930'] → 시뮬레이션: 500 에러
  2. 재시도 버튼 클릭
  3. 정상 성공
- **기대 결과**: 2차 시도에서 성공, 종목 추가됨

#### TC-INT-050: 정상 - 오프라인 대응
- **전제조건**: 브라우저 DevTools에서 오프라인 상태 시뮬레이션
- **시나리오**: 종목 추가 시도
- **기대 결과**:
  - 에러 메시지: "네트워크 연결을 확인해주세요"
  - UI 상태 유지

---

### 섹션 7: 성능 테스트 (1개 TC)

#### TC-PERF-051: 성능 - 100개 종목 추가 시간
- **전제조건**: 빈 상태
- **입력**: POST /api/stocks/specific/add 100개 종목 일괄
- **기대 결과**:
  - **응답 시간**: < 2초 (목표: < 500ms, 실제는 일괄이므로 + 1.5초 허용)
  - **메모리 증가**: < 5MB
  - **CPU 사용률**: < 20%
- **점검**: 브라우저 DevTools Performance 탭에서 기록

---

## 테스트 실행 계획

### 환경
- 테스트 DB: SQLite (테스트용)
- 백엔드 서버: localhost:8000 (테스트 모드)
- 브라우저: Chrome 최신 버전
- 해상도: 1920x1080

### 실행 순서
1. API 테스트 (TC-API-001 ~ 030): Jest + Postman
2. UI 테스트 (TC-UI-031 ~ 040): 브라우저 수동 + Selenium (선택)
3. 통합 테스트 (TC-INT-041 ~ 050): 엔드-투-엔드
4. 성능 테스트 (TC-PERF-051): Lighthouse + DevTools

### 예상 소요 시간
- API 테스트: 15분 (자동화)
- UI 테스트: 30분 (수동)
- 통합 테스트: 20분
- 성능 테스트: 10분
- **총 약 75분**

---

## 통과 기준

| 기준 | 대상 | 기준값 |
|------|------|--------|
| **테스트 통과율** | 전체 51개 | ≥ 95% (최대 2개 실패 허용, 비주요 기능) |
| **API 응답 코드** | 모든 API | 200, 400 (성공/오류 정확성) |
| **UI 반응성** | 모든 UI 조작 | < 1초 (지각 가능한 지연 없음) |
| **성능** | 100개 추가 | < 2초 (기준: < 500ms + 여유) |
| **메모리** | 최대 사용량 | < 200MB |
| **커버리지** | 코드 라인 | ≥ 80% |

---

## 테스트 결과 기록

```
[테스트 실행 시작 일시]: 2026-02-08 14:50:00
[테스트 환경]: Localhost, SQLite, Chrome
[실행자]: LLD_테스트_담당자

[섹션별 결과]
- API 테스트 (30 TC): __/30 통과
- UI 테스트 (10 TC): __/10 통과
- 통합 테스트 (10 TC): __/10 통과
- 성능 테스트 (1 TC): __/1 통과

[최종 통과율]: __% (__/51)

[이슈 발견]:
(버그 또는 개선 사항 기록)

[서명]: __________  [날짜]: __________
```

---

**다음 단계**: 이 테스트 문서를 바탕으로 TICKET-012(테스트 환경)에서 실제 테스트를 실행합니다.
