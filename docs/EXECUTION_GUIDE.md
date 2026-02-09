# 서비스 실행 및 테스트 가이드

**프로젝트**: PrivateTrade Backtesting Simulator  
**최신 버전**: 2.0.0  
**마지막 업데이트**: 2026년 2월 8일  

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
3. [환경 1: Docker Compose (권장)](#환경-1-docker-compose-권장)
4. [환경 2: 로컬 개발 환경](#환경-2-로컬-개발-환경)
5. [서비스 실행 및 테스트](#서비스-실행-및-테스트)
6. [API 테스트](#api-테스트)
7. [프론트엔드 접근](#프론트엔드-접근)
8. [로그 확인](#로그-확인)
9. [문제 해결](#문제-해결)

---

## 🔧 사전 요구사항

### 필수 설치 항목

#### 1. Git
```bash
git --version
```
필요 시 설치: https://git-scm.com/

#### 2. Node.js & npm (v16 이상)
```bash
node --version   # v16.0.0 이상
npm --version    # 7.0.0 이상
```
필요 시 설치: https://nodejs.org/

#### 3. Python (v3.8 이상)
```bash
python --version  # 3.8 이상
pip --version
```
필요 시 설치: https://www.python.org/

#### 4. Docker & Docker Compose
```bash
docker --version        # Docker 20.10 이상
docker-compose --version  # 1.29 이상
```
필요 시 설치: https://www.docker.com/

#### 5. SQLite3 (선택사항)
```bash
sqlite3 --version
```
필요 시 설치: https://www.sqlite.org/

---

## 📦 로컬 개발 환경 설정

### 1단계: 프로젝트 클론
```bash
cd c:\Dev
git clone <repository-url> privatetrade
cd privatetrade
```

### 1.5단계: 백엔드 서버 파일 생성 (필요시)

`backend/server.js` 파일이 없으면 아래 명령으로 생성합니다:

```bash
# Windows PowerShell에서 실행:
# 또는 문서의 "단계 1: Node.js 의존성 설치" 완료 후 자동 확인

# 파일이 없는지 확인
ls backend\server.js 2>$null || echo "server.js 파일 없음"

# 있으면 스킵, 없으면 생성 필요 (자동으로 처리됨)
```

> **참고**: `backend/server.js`는 Express.js 기반의 메인 서버 파일입니다. 없으면 이어지는 단계에서 생성되거나 깃 클론 시 포함되어야 합니다.

### 2단계: 저장소 상태 확인
```bash
# 기본 폴더 구조 확인
ls -la

# 출력 예상:
# backend/
#   ├── modules/
#   ├── routes/
#   ├── utils/
#   └── server.js (필수 - 없으면 다음 단계에서 생성)
# db/
# docs/
# frontend/
# py_backtest/
# test-data/
# docker-compose-test.yml
# package.json (root 레벨)
# Jenkinsfile
```

> **중요**: `backend/server.js` 파일이 없으면 단계 1에서 생성됩니다. 수동으로 먼저 생성하려면 아래를 참고하세요.

---

## 🐳 환경 1: Docker Compose (권장)

**장점**: 독립적인 테스트 환경, 의존성 격리, 빠른 시작

### 실행 방법

```bash
# 프로젝트 루트로 이동
cd c:\Dev\privatetrade

# 1. Docker 이미지 빌드 및 컨테이너 실행
docker-compose -f docker-compose-test.yml up -d

# 2. 서비스 상태 확인
docker-compose -f docker-compose-test.yml ps

# 예상 출력:
# NAME                         STATUS              PORTS
# privatetrade-test-db        Up 10s (healthy)    -
# privatetrade-backend-test   Up 8s (healthy)     0.0.0.0:8000->8000/tcp
# privatetrade-mock-api       Up 7s (healthy)     0.0.0.0:1080->1080/tcp
# privatetrade-test-runner    Exited (0)          -
```

### 서비스 접근

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Backend API** | `http://localhost:8000` | 백엔드 서버 |
| **헬스 체크** | `http://localhost:8000/api/health` | 서버 상태 확인 |
| **Mock API** | `http://localhost:1080` | 외부 API 모킹 |

### 서비스 중지 및 정리
```bash
# 1. 서비스 중지
docker-compose -f docker-compose-test.yml stop

# 2. 컨테이너 제거
docker-compose -f docker-compose-test.yml down

# 3. 이미지 포함 완전 제거
docker-compose -f docker-compose-test.yml down -v --rmi all
```

---

## 🖥️ 환경 2: 로컬 개발 환경

**장점**: 빠른 수정/재실행, 상세 로그 확인, 디버깅 용이

### 단계 1: Node.js 의존성 설치

```bash
cd c:\Dev\privatetrade

# 1. 루트 레벨에 package.json 생성 (필요시)
# 만약 루트 폴더에 package.json이 없으면:
cat > package.json << EOF
{
  "name": "privatetrade",
  "version": "2.0.0",
  "description": "Stock Trading Strategy Backtesting Simulator",
  "main": "backend/server.js",
  "scripts": {
    "start": "node backend/server.js",
    "dev": "nodemon backend/server.js",
    "build": "echo 'Build complete'",
    "test:unit": "jest backend/",
    "test:integration": "jest --config=jest.integration.config.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sqlite3": "^5.1.6",
    "body-parser": "^1.20.2",
    "cors": "^2.8.5",
    "dotenv": "^16.0.3",
    "child_process": "^1.0.2"
  },
  "devDependencies": {
    "nodemon": "^2.0.20",
    "jest": "^29.5.0"
  }
}
EOF

# 2. 루트 레벨 의존성 설치
npm install

# 3. 설치 확인
npm list --depth=0

# 예상 출력:
# privatetrade@2.0.0
# ├── body-parser@1.20.2
# ├── cors@2.8.5
# ├── dotenv@16.0.3
# ├── express@4.18.2
# └── sqlite3@5.1.6
```

### 단계 2: Python 의존성 설치

```bash
# 1. Python 가상 환경 생성
python -m venv venv

# 2. 가상 환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt

# 설치 확인:
pip list
```

> **참고**: 현재 디렉토리에 `requirements.txt`가 없으면 다음을 생성:
> ```bash
> cat > requirements.txt << EOF
> pandas>=1.3.0
> numpy>=1.21.0
> pytest>=7.0.0
> pytest-cov>=3.0.0
> Flask>=2.0.0
> EOF
> ```

### 단계 3: 데이터베이스 초기화

```bash
# SQLite 데이터베이스 생성 및 마이그레이션
cd c:\Dev\privatetrade
sqlite3 backtest.db < db/init-test.sql

# 마이그레이션 실행
sqlite3 backtest.db < db/migrations/001_add_specific_stock_selection.sql

# 데이터베이스 확인
sqlite3 backtest.db ".schema"
```

### 단계 4: 백엔드 서버 시작

```bash
cd c:\Dev\privatetrade

# package.json에 정의된 스크립트 확인
npm run

# 예상 출력:
# start    - 프로덕션 서버 시작
# dev      - 개발 서버 시작 (nodemon 포함)
# build    - 프로젝트 빌드
# test:unit - 유닛 테스트
# test:integration - 통합 테스트

# 개발 환경에서 시작 (권장) - 파일 변경 시 자동 재시작
npm run dev

# 또는 프로덕션 환경
npm start
```

**예상 출력**:
```
[nodemon] 2.0.20
[nodemon] to restart at any time, enter `rs`
[nodemon] watching path(s): *.*
[nodemon] watching extensions: js,json
[nodemon] starting `node backend/server.js`
Server is running on port 8000
Frontend served at http://localhost:8000
API base URL: http://localhost:8000/api
```

### 단계 5: 백테스팅 엔진 시작 (별도 터미널)

```bash
# 가상 환경 활성화
venv\Scripts\activate

# Python 워커 실행
cd c:\Dev\privatetrade\py_backtest
python worker.py

# 또는
python -m worker
```

**예상 출력**:
```
Starting Python backtest worker...
Worker initialized: <PID>
Listening for commands...
```

---

## 🚀 서비스 실행 및 테스트

### 서비스 시작 체크리스트

#### Docker Compose 환경
```bash
# 1. 서비스 실행
docker-compose -f docker-compose-test.yml up -d

# 2. 모든 서비스 상태 확인
docker-compose -f docker-compose-test.yml ps

# 3. 백엔드 헬스 체크
curl http://localhost:8000/api/health

# 예상 응답:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "uptime": 5,
#   "services": {
#     "database": "connected",
#     "python_worker": "ready"
#   }
# }

# 4. 로그 확인
docker-compose -f docker-compose-test.yml logs -f backend-test
```

#### 로컬 개발 환경
```bash
# 터미널 1: 백엔드 서버
cd c:\Dev\privatetrade
npm run dev

# 터미널 2: Python 백테스팅 엔진
cd c:\Dev\privatetrade
venv\Scripts\activate
cd py_backtest
python worker.py

# 터미널 3: API 테스트
curl http://localhost:8000/api/health
```

---

## 🔌 API 테스트

### 1. 헬스 체크
```bash
curl -X GET http://localhost:8000/api/health
```

**응답**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 10
}
```

### 2. 주식 모드 설정 (신규 기능)
```bash
curl -X POST http://localhost:8000/api/stocks/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "specific"}'
```

**응답**:
```json
{
  "success": true,
  "current_mode": "specific"
}
```

### 3. 특정 종목 추가
```bash
curl -X POST http://localhost:8000/api/stocks/specific/add \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["005930", "000660"]
  }'
```

**응답**:
```json
{
  "success": true,
  "selected_count": 2,
  "selected_stocks": [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"}
  ]
}
```

### 4. 선택된 종목 조회
```bash
curl -X GET http://localhost:8000/api/stocks/specific
```

**응답**:
```json
{
  "selected_count": 2,
  "selected_stocks": [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"}
  ]
}
```

### 5. 백테스팅 시작 (주식 모드 포함)
```bash
curl -X POST http://localhost:8000/api/backtest/start \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "MA20_50",
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "initial_capital": 10000000,
    "stock_mode": "specific"
  }'
```

**응답**:
```json
{
  "success": true,
  "backtest_id": "bt-20260208-001",
  "status": "running"
}
```

### 6. 백테스팅 진행 상황 확인
```bash
curl -X GET http://localhost:8000/api/backtest/progress?id=bt-20260208-001
```

**응답**:
```json
{
  "backtest_id": "bt-20260208-001",
  "status": "running",
  "progress_percent": 45,
  "current_date": "2024-06-15",
  "total_trades": 125
}
```

### 7. 백테스팅 결과 조회
```bash
curl -X GET http://localhost:8000/api/backtest/result/bt-20260208-001
```

**응답**:
```json
{
  "backtest_id": "bt-20260208-001",
  "status": "completed",
  "performance": {
    "total_return": "45.32%",
    "sharpe_ratio": 1.85,
    "max_drawdown": "-12.5%",
    "total_trades": 247
  },
  "results_file": "/api/results/bt-20260208-001.csv"
}
```

---

## 🌐 프론트엔드 접근

### 단계 1: 서버 실행 확인
```bash
# 로컬 개발 환경
npm run dev

# Docker 환경
docker-compose -f docker-compose-test.yml up -d
```

### 단계 2: 브라우저에서 접속
```
http://localhost:8000
```

### 단계 3: 주요 페이지

| 페이지 | URL | 설명 |
|--------|-----|------|
| **메인** | `/` | 백테스팅 설정 |
| **특정 종목 선택** | `/pages/specific-stock-selection.html` | 종목 선택 UI |
| **결과 조회** | `/results` | 백테스팅 결과 |

### 단계 4: 프론트엔드 테스트
```bash
# 특정 종목 선택 페이지 접속
http://localhost:8000/pages/specific-stock-selection.html

# 기능 테스트
1. "특정 종목 선택" 버튼 클릭
2. 종목 코드 입력 (예: 005930)
3. "추가" 버튼 클릭
4. 백테스팅 시작
```

---

## 📊 로그 확인

### Docker Compose 환경

#### 백엔드 로그
```bash
# 실시간 로그 보기
docker-compose -f docker-compose-test.yml logs -f backend-test

# 최근 100줄 보기
docker-compose -f docker-compose-test.yml logs --tail=100 backend-test

# 타임스탐프 포함
docker-compose -f docker-compose-test.yml logs --timestamps backend-test
```

#### 데이터베이스 로그
```bash
docker-compose -f docker-compose-test.yml logs -f test-db
```

#### 전체 서비스 로그
```bash
docker-compose -f docker-compose-test.yml logs -f
```

### 로컬 개발 환경

#### 백엔드 서버 로그
```
// npm run dev 실행 시 콘솔에 표시
[nodemon] restarting due to changes...
Server is running on port 8000
```

#### Python 워커 로그
```
Starting Python backtest worker...
Worker initialized: <PID>
[INFO] Processing backtest task...
```

#### 애플리케이션 로그 파일
```bash
# 현재 경로 확인
pwd

# 로그 파일 조회 (있는 경우)
cat logs/app.log
tail -f logs/app.log
```

---

## 🧪 테스트 실행

### 유닛 테스트
```bash
cd c:\Dev\privatetrade

# 모든 유닛 테스트 실행
npm run test:unit

# 커버리지 리포트 포함
npm run test:unit -- --coverage

# 특정 파일 테스트
npm test -- StockFilter.test.js
```

### 통합 테스트
```bash
# 로컬 환경 (권장)
cd c:\Dev\privatetrade
npm run test:integration

# 또는 Docker 환경
docker-compose -f docker-compose-test.yml up -d
docker-compose -f docker-compose-test.yml exec backend-test npm run test:integration
```

### Python 테스트
```bash
# 가상 환경 활성화
venv\Scripts\activate

# pytest 실행
pytest py_backtest/ -v

# 커버리지 포함
pytest py_backtest/ --cov=py_backtest
```

### 테스트 결과 조회
```bash
# 테스트 리포트 확인
ls -la docs/test/lld/

# JUnit 리포트 열기
test-results/junit-report.xml

# HTML 커버리지 리포트
open coverage/index.html
```

---

## 🐛 문제 해결

### 1. "Cannot find module 'backend/server.js'" 오류

**증상**:
```
Error: Cannot find module 'C:\Dev\privatetrade\backend\server.js'
```

**원인**: `backend/server.js` 파일이 없음 (초기 설정 누락)

**해결 방법**:

```bash
# 1. backend/server.js 파일이 있는지 확인
ls backend\server.js

# 2. 파일이 없으면:
#    - 백업 저장소에서 다시 클론
#    - 또는 프로젝트 담당자에게 backend/server.js 파일 요청
#    - 또는 다음 정보로 파일 생성:
#
#    nodejs express 프레임워크 기반 메인 서버 파일
#    주요 내용:
#    - Express 서버 초기화
#    - routes/stocks.js 라우트 연결
#    - /api/health, /api/backtest/*, /api/stocks/* 엔드포인트
#    - 포트 8000에서 수신
#    - 정적 파일 서빙 (frontend 폴더)

# 3. 파일이 생성되었으면 다시 실행
npm run dev
```

**참고**: 이 가이드의 "1.5단계: 백엔드 서버 파일 생성" 섹션을 참고하세요.

---

### 3. "포트 8000이 이미 사용 중입니다" 오류

```bash
# Windows: 프로세스 확인 및 종료
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux: 프로세스 확인 및 종료
lsof -i :8000
kill -9 <PID>

# 또는 다른 포트 사용
PORT=3001 npm run dev
```

### 4. Docker 컨테이너가 시작되지 않음

```bash
# 1. Docker 데몬 확인
docker ps

# 2. 이전 컨테이너 정리
docker-compose -f docker-compose-test.yml down -v

# 3. 이미지 재빌드
docker-compose -f docker-compose-test.yml build --no-cache

# 4. 로그 확인
docker-compose -f docker-compose-test.yml logs
```

### 3. 데이터베이스 마이그레이션 실패

```bash
# 1. 데이터베이스 초기화
rm backtest.db

# 2. 초기화 스크립트 실행
sqlite3 backtest.db < db/init-test.sql

# 3. 마이그레이션 실행
sqlite3 backtest.db < db/migrations/001_add_specific_stock_selection.sql

# 4. 데이터베이스 확인
sqlite3 backtest.db ".tables"
sqlite3 backtest.db ".schema config"
```

### 5. npm 의존성 설치 오류

**증상**: `npm ERR! code ENOENT` 또는 `package.json: No such file or directory`

```bash
# 1. package.json 확인
ls -la package.json
# 없으면 생성 (위의 "단계 1: Node.js 의존성 설치" 참고)

# 2. 캐시 정리
npm cache clean --force

# 3. node_modules 삭제
rm -rf node_modules package-lock.json

# 4. 재설치
npm install

# 5. 설치 목록 확인
npm list
```

**자주 발생하는 원인**:
- `package.json` 파일이 없음 → 위의 "단계 1"에서 생성
- 백엔드 폴더에서 npm install 실행 → 루트 폴더에서 실행
- npm 버전 구식 → `npm install -g npm@latest` 로 업그레이드

### 6. Python 가상 환경 문제

```bash
# 1. 기존 가상환경 삭제
rm -rf venv

# 2. 새 가상환경 생성
python -m venv venv

# 3. 활성화 및 설치
venv\Scripts\activate
pip install -r requirements.txt
```

### 7. API 호출 실패

```bash
# 1. 서버 상태 확인
curl http://localhost:8000/api/health

# 2. 서버가 실행 중인지 확인
# 터미널에서 npm run dev 실행 후 다시 시도

# 3. 네트워크 연결 확인
ping localhost

# 4. 방화벽 확인 (Windows)
#    설정 > 보안 > 방화벽 > 앱 허용
#    Node.js (또는 npm)를 "개인 네트워크" 허용 목록에 추가

# 5. 포트 확인
netstat -ano | findstr :8000
# 8000 포트가 다른 프로세스에서 사용 중이면:
taskkill /PID <PID> /F

# 6. 상세 로그 확인
cd c:\Dev\privatetrade
npm run dev
# 콘솔 로그 확인 - [nodemon], error 메시지 등
```

---

## 📝 체크리스트

### ✅ 초기 설정
- [ ] Node.js & npm 설치 확인
- [ ] Python 설치 확인
- [ ] Docker & Docker Compose 설치 확인
- [ ] Git 프로젝트 클론
- [ ] npm 의존성 설치 완료
- [ ] Python 가상환경 생성 및 패키지 설치 완료
- [ ] 데이터베이스 초기화 완료

### ✅ 서비스 실행
- [ ] Docker Compose 또는 로컬 환경 선택
- [ ] 백엔드 서버 실행 확인
- [ ] Python 백테스팅 엔진 실행 확인
- [ ] 헬스 체크 API 성공
- [ ] 프론트엔드 접근 가능

### ✅ 기본 테스트
- [ ] 헬스 체크 API 테스트
- [ ] 특정 종목 추가 API 테스트
- [ ] 백테스팅 시작 API 테스트
- [ ] 결과 조회 API 테스트
- [ ] 프론트엔드 특정 종목 선택 페이지 로드

### ✅ 고급 테스트
- [ ] 유닛 테스트 실행
- [ ] 통합 테스트 실행
- [ ] 커버리지 리포트 확인
- [ ] 모든 테스트 통과

---

## 📚 추가 문서

- [개발 가이드](./docs/README.md)
- [HLD 문서](./docs/hld/hld_20260208.md)
- [LLD 문서](./docs/lld/lld_20260208.md)
- [배포 계획](./docs/deployment/deployment-plan.md)
- [빌드 로그](./docs/BUILD_LOG.md)

---

## 💡 팁

1. **개발 중 빠른 재시작**: `npm run dev` 사용 (nodemon으로 자동 재시작)
2. **문제 디버깅**: 로그를 먼저 확인 후 문제 재현
3. **테스트 우선**: 기능 추가 전 테스트 코드 작성
4. **깃 커밋**: 작은 단위로 자주 커밋
5. **CI/CD**: Jenkins 파이프라인 활용 (Jenkinsfile 참고)

---

**문제가 발생하면**: `docs/log/` 폴더의 로그를 확인하거나 위의 "문제 해결" 섹션을 참고하세요.
