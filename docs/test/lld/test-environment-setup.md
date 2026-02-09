# LLD 테스트 환경 설정 가이드

**작성일**: 2026년 2월 8일  
**버전**: 2.0  
**대상**: LLD 테스트 실행 담당자

---

## 1. 시스템 요구사항

### 하드웨어
- CPU: 2코어 이상
- 메모리: 4GB 이상
- 디스크: 2GB 이상 (테스트 DB + 로그)

### 소프트웨어
- Docker & Docker Compose 설치 (최신 버전)
  ```bash
  docker --version
  docker-compose --version
  ```
- Node.js 18.x 이상 (로컬 테스트 시)
- npm >= 9.x
- SQLite3 CLI (선택)

---

## 2. 테스트 환경 구성

### 2.1 디렉토리 구조
```
privatetrade/
├── docker-compose-test.yml      # 테스트 환경 정의
├── test-data/
│   ├── backtest-test.db         # 테스트 데이터베이스 (생성됨)
│   ├── mock-stocks.json         # Mock 종목 데이터
│   └── mockserver-init.json     # Mock API 설정
├── test-results/
│   ├── junit-report.xml         # 테스트 결과 (생성됨)
│   └── coverage-report.html     # 커버리지 보고서 (생성됨)
├── db/
│   ├── migrations/
│   │   └── 001_add_specific_stock_selection.sql
│   └── init-test.sql            # 테스트 DB 초기화 스크립트
├── backend/
│   ├── Dockerfile.test          # 테스트용 Docker 이미지
│   ├── package.json
│   └── src/
└── docs/test/lld/
    ├── test-cases-specific-stocks.md  # 51개 테스트 케이스 (TICKET-011)
    └── test-environment-setup.md      # 이 파일
```

---

## 3. 테스트 환경 시작

### 3.1 기본 시작 (모든 서비스)

```bash
# 테스트 환경 디렉토리로 이동
cd c:\Dev\privatetrade

# 모든 서비스 시작
docker-compose -f docker-compose-test.yml up -d

# 상태 확인
docker-compose -f docker-compose-test.yml ps
```

**예상 출력:**
```
NAME                      COMMAND          STATUS
privatetrade-test-db     "sqlite3 ..."    Up (healthy)
privatetrade-backend-test "npm run..."    Up (healthy)
privatetrade-mock-api    "mockserver..."  Up (healthy)
privatetrade-test-runner  "npm run..."    Exited (0)  [테스트 완료]
```

### 3.2 개별 서비스 시작 (필요시)

```bash
# 데이터베이스만 시작
docker-compose -f docker-compose-test.yml up -d test-db

# 백엔드 서버만 시작
docker-compose -f docker-compose-test.yml up -d backend-test

# Mock API만 시작
docker-compose -f docker-compose-test.yml up -d mock-api
```

---

## 4. 데이터베이스 초기화

### 4.1 데이터베이스 생성 및 마이그레이션

```bash
# 테스트 DB 디렉토리 생성
mkdir -p test-data

# SQLite 데이터베이스 생성 및 초기화
sqlite3 test-data/backtest-test.db < db/init-test.sql

# 마이그레이션 적용
sqlite3 test-data/backtest-test.db < db/migrations/001_add_specific_stock_selection.sql

# 검증: 테이블 목록 확인
sqlite3 test-data/backtest-test.db ".tables"
```

**예상 출력:**
```
config            backtest_result  backtest_session  trade_detail
```

### 4.2 테스트 데이터 확인

```bash
# config 테이블 조회
sqlite3 test-data/backtest-test.db "SELECT id, stock_mode, selected_specific_stocks FROM config LIMIT 5;"
```

**예상 출력:**
```
1|all|
2|filtered|
3|specific|["005930","000660"]
4|specific|["005930","000660","068270","035720","012330","051910","017670","090430"]
```

---

## 5. 백엔드 서버 확인

### 5.1 헬스 체크
```bash
curl http://localhost:8000/api/health

# 또는 PowerShell
(Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing).Content
```

**예상 응답:**
```json
{
  "status": "ok",
  "version": "2.0",
  "timestamp": "2026-02-08T15:15:00Z"
}
```

### 5.2 API 엔드포인트 테스트

#### 테스트 1: GET /api/stocks/specific
```bash
curl -X GET http://localhost:8000/api/stocks/specific

# 또는 PowerShell
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/stocks/specific" -Method Get
$response | ConvertTo-Json
```

**예상 응답:**
```json
{
  "current_mode": "all",
  "selected_count": 0,
  "selected_stocks": []
}
```

#### 테스트 2: POST /api/stocks/mode
```bash
curl -X POST http://localhost:8000/api/stocks/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"specific"}'

# PowerShell
$body = @{"mode"="specific"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/stocks/mode" -Method Post -Body $body -ContentType "application/json"
```

**예상 응답:**
```json
{
  "success": true,
  "current_mode": "specific"
}
```

#### 테스트 3: POST /api/stocks/specific/add
```bash
curl -X POST http://localhost:8000/api/stocks/specific/add \
  -H "Content-Type: application/json" \
  -d '{"codes":["005930","000660"]}'

# PowerShell
$body = @{"codes"=@("005930","000660")} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/stocks/specific/add" -Method Post -Body $body -ContentType "application/json"
```

**예상 응답:**
```json
{
  "success": true,
  "selected_count": 2,
  "selected_stocks": ["005930", "000660"]
}
```

---

## 6. 테스트 실행

### 6.1 전체 통합 테스트 실행 (자동)

```bash
# Jest 테스트 실행 (모든 API & 통합 테스트)
npm run test:integration

# 또는 docker-compose를 통해
docker-compose -f docker-compose-test.yml up test-runner --abort-on-container-exit
```

### 6.2 단위 테스트만 실행

```bash
npm run test:unit
```

### 6.3 특정 테스트 파일만 실행

```bash
npm test -- --testPathPattern="stocks" --verbose
```

---

## 7. 테스트 결과 수집

### 7.1 테스트 결과 확인

```bash
# 결과 디렉토리 확인
ls -la test-results/

# JUnit 리포트 확인
cat test-results/junit-report.xml

# 커버리지 리포트 확인 (HTML)
open test-results/coverage-report.html  # macOS
start test-results/coverage-report.html # Windows
```

### 7.2 로그 확인

```bash
# 백엔드 로그
docker logs privatetrade-backend-test | tail -50

# 테스트 로그
docker logs privatetrade-test-runner | tail -100
```

---

## 8. 성능 프로파일링

### 8.1 API 응답 시간 측정

```bash
# 단일 API 호출 시간 측정
time curl -X GET http://localhost:8000/api/stocks/specific

# 100회 반복 호출 평균 시간
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8000/api/stocks/specific
done | awk '{sum+=$1} END {print "Average: " sum/NR " seconds"}'
```

### 8.2 메모리 사용량 모니터링

```bash
# Docker 예정 정보 확인
docker stats privatetrade-backend-test --no-stream

# 실시간 모니터링 (Ctrl+C로 중지)
docker stats privatetrade-backend-test
```

---

## 9. 환경 정리

### 9.1 모든 컨테이너 중지

```bash
docker-compose -f docker-compose-test.yml down
```

### 9.2 테스트 데이터 삭제

```bash
rm -rf test-data/backtest-test.db  # 테스트 DB 삭제
rm -rf test-results/*              # 테스트 결과 삭제

# 또는 PowerShell
Remove-Item -Path test-data/backtest-test.db -Force
Remove-Item -Path test-results/* -Force
```

### 9.3 Docker 이미지 정리

```bash
docker-compose -f docker-compose-test.yml down --rmi all
```

---

## 10. 트러블슈팅

### 10.1 컨테이너 시작 실패
```bash
# 로그 상세 확인
docker-compose -f docker-compose-test.yml logs -f test-db

# 컨테이너 재시작
docker-compose -f docker-compose-test.yml restart test-db
```

### 10.2 데이터베이스 연결 오류
```bash
# SQLite DB 파일 권한 확인
ls -la test-data/backtest-test.db

# 권한 변경 (필요시)
chmod 666 test-data/backtest-test.db
```

### 10.3 포트 충돌
```bash
# 포트 8000 점유 프로세스 확인 (Windows)
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /PID <PID> /F
```

### 10.4 권한 오류
```bash
# Docker daemon 재시작
sudo systemctl restart docker

# 또는 Docker Desktop 앱 재실행
```

---

## 11. CI/CD 통합

### 11.1 GitHub Actions (예시)
```yaml
name: Test Environment

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start test environment
        run: docker-compose -f docker-compose-test.yml up -d
      
      - name: Wait for services
        run: |
          docker-compose -f docker-compose-test.yml logs
          sleep 10
      
      - name: Run tests
        run: docker-compose -f docker-compose-test.yml up test-runner
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

---

## 12. 체크리스트

테스트 환경 구축 완험 확인:

- [ ] Docker & Docker Compose 설치 확인
- [ ] 데이터베이스 생성 및 마이그레이션 완료
- [ ] 테스트 데이터 로드 확인
- [ ] 백엔드 서버 헬스 체크 성공
- [ ] API 엔드포인트 응답 확인 (4개)
- [ ] 통합 테스트 실행 성공
- [ ] 테스트 결과 수집 완료
- [ ] 성능 지표 측정 완료
- [ ] 모든 로그 정상 기록 확인
- [ ] 환경 정리 및 문서화 완료

---

## 참고

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Jest Testing Framework](https://jestjs.io/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

**작성자**: LLD_테스트_환경_담당자  
**최종 수정**: 2026-02-08  
