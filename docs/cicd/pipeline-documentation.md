# CI/CD 파이프라인 문서

**작성일**: 2026년 2월 8일  
**버전**: 1.0  
**대상**: DevOps / CI/CD 담당자

---

## 1. 파이프라인 개요

### 1.1 목표
- 자동화된 빌드, 테스트, 배포 프로세스
- 코드 품질 및 보안 검증
- 무중단 배포 (Blue-Green)
- 실시간 모니터링 및 롤백 계획

### 1.2 플랫폼
- **CI/CD 툴**: GitHub Actions (또는 GitLab CI / Jenkins)
- **컨테이너**: Docker
- **배포 환경**: 스테이징 (develop), 프로덕션 (v* 태그)
- **오케스트레이션** (선택): Kubernetes 또는 Docker Swarm

### 1.3 파이프라인 단계 (6단계)

```
┌──────┐    ┌──────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│ Push │───▶│Build │───▶│ Test    │───▶│ Quality  │───▶│ Docker   │───▶│Deploy  │
│      │    │&Lint │    │&Lint    │    │ & Sec.   │    │ Build    │    │To Env  │
└──────┘    └──────┘    └─────────┘    └──────────┘    └──────────┘    └────────┘
              ↓            ↓              ↓               ↓        │         │
           (fail → abort) Artifact    Coverage         Docker     │    Staging(dev)
                         Upload        Report          Image      │    Prod(tag v*)
                                                      Push(ghcr) │         │
                                                                  └─▶ Smoke Test
                                                                      ↓
                                                                   OK→ Go Live
                                                                   NG→ Rollback
```

---

## 2. 파이프라인 단계별 상세

### 2.1 STAGE 1: Build & Lint

**목표**: 코드 컴파일 및 기본 품질 검사

| 항목 | 내용 |
|------|------|
| **트리거** | main, develop 브랜치 push, PR |
| **러너** | ubuntu-latest |
| **작업** | npm ci, npm run build, npm run lint |
| **아티팩트** | dist/, backend/, frontend/ |
| **소요 시간** | ~3분 |

**실패 케이스**:
- Lint 오류 발견 → 다음 단계 진행 불가 (warn만, continue)
- 빌드 실패 → 파이프라인 중단

### 2.2 STAGE 2: Unit & Integration Tests

**목표**: 코드 품질 및 기능 검증

| 항목 | 내용 |
|------|------|
| **선행 조건** | STAGE 1 성공 |
| **테스트 범위** | 단위 테스트, 통합 테스트 (51개 TC) |
| **커버리지 목표** | ≥ 80% |
| **테스트 DB** | SQLite (in-memory) |
| **소요 시간** | ~10분 |

**매트릭**:
- 테스트 통과율 ≥ 95%
- 커버리지 ≥ 80%
- 응답 시간 < 500ms

**실패 처리**:
- 테스트 실패 → 파이프라인 중단, 개발자 알림

### 2.3 STAGE 3: Security & Code Quality

**목표**: 보안 취약점 및 코드 품질 검사

| 항목 | 내용 |
|------|------|
| **선행 조건** | STAGE 1 성공 |
| **검사 항목** | Vulnerability (npm audit), License check, SonarQube (선택) |
| **소요 시간** | ~5분 |

**스캔 도구**:
- npm audit: npm 패키지 취약점 검사
- SonarQube: 코드 품질 (선택)
- SNYK: 의존성 취약점 (선택)

**기준**:
- npm audit: moderate 이상 취약점 경고 (fail 아님)
- 라이선스: GPL 등 제약 라이선스 확인

### 2.4 STAGE 4: Build Docker Image

**목표**: Docker 이미지 빌드 및 푸시

| 항목 | 내용 |
|------|------|
| **선행 조건** | STAGE 1, 2, 3 모두 성공 |
| **이미지 레지스트리** | Docker Hub (privatetrade/backtesting-simulator) |
| **태깅 전략** | git 브랜치, 커밋 SHA, 세마필 버전 (v*.*.* ) |
| **소요 시간** | ~8분 (캐시 포함) |

**이미지 이름 예시**:
```
docker.io/privatetrade/backtesting-simulator:main
docker.io/privatetrade/backtesting-simulator:develop
docker.io/privatetrade/backtesting-simulator:v2.0.0
docker.io/privatetrade/backtesting-simulator:sha-abc123def
```

**빌드 최적화**:
- BuildKit 사용 (DOCKER_BUILDKIT=1)
- 레이어 캐싱 (--cache-from registry)
- 멀티스테이지 빌드

### 2.5 STAGE 5: Deploy to Staging

**목표**: 개발 환경(develop)에 배포 및 검증

| 항목 | 내용 |
|------|------|
| **트리거** | develop 브랜치 push |
| **배포 대상** | staging 환경 (localhost:3000) |
| **배포 방식** | docker-compose up 또는 kubectl apply |
| **소요 시간** | ~5분 |

**배포 후 검증**:
- Smoke 테스트: GET /api/health (30회, 2초 간격)
- 헬스 체크 통과 확인
- 기본 API 응답 확인

**실패 처리**:
- 헬스 체크 실패 → Slack 알림, 수동 조사 필요

### 2.6 STAGE 6: Deploy to Production

**목표**: 프로덕션 환경에 무중단 배포

| 항목 | 내용 |
|------|------|
| **트리거** | v* 태그 푸시 (세마틱 버저닝) |
| **배포 대상** | production 환경 |
| **배포 방식** | Blue-Green 무중단 배포 |
| **데이터 마이그레이션** | 자동 실행 (ALTER TABLE 등) |
| **소요 시간** | ~10분 |

**Blue-Green 배포 프로세스**:

```
1. Blue (기존)
   ├─ 트래픽: 100%
   └─ Instance: prod-app-blue (v1.9.0)

   ↓ 배포 시작

2. Green (신규) 배포
   ├─ Docker pull/run
   ├─ DB 마이그레이션
   ├─ 헬스 체크 (60회, 5초 간격)
   └─ Instance: prod-app-green (v2.0.0)

   ↓ 검증 완료

3. 트래픽 전환
   ├─ LB 설정 변경
   ├─ Blue: 트래픽 0% → Green으로 전환
   └─ Green: 트래픽 100%

   ↓ 모니터링

4. Blue 대기 (롤백용)
   ├─ Blue 유지 (60분 ~ 24시간)
   ├─ 이슈 발생 시 즉시 롤백 가능
   └─ 문제 없으면 Blue 종료
```

**배포 실패 및 롤백**:

```
배포 중 오류 발생 (예: 헬스 체크 실패)
  ↓
자동 롤백 트리거
  ↓
LB 설정 → Blue로 재전환 (원래대로)
  ↓
트래픽 100% Blue로 복구
  ↓
Green 인스턴스 종료
  ↓
RCA (근본 원인 분석) 및 호트팩스 준비
```

**모니터링 (배포 후 72시간)**:
- 에러 로그 수집
- 성능 메트릭 (응답 시간, CPU, 메모리)
- 사용자 보고 (슬랙 채널)
- 24시간: 문제 없으면 Blue 환경 정리

---

## 3. 환경 변수 및 시크릿

### 3.1 GitHub Secrets (설정 필요)

| 이름 | 용도 | 예시 |
|------|------|------|
| `DOCKER_USERNAME` | Docker Hub 로그인 | `devops-user` |
| `DOCKER_PASSWORD` | Docker Hub 비밀번호 | `*** (토큰)` |
| `KUBECONFIG_STAGING` | Kubernetes 설정 (스테이징) | base64 인코딩 |
| `KUBECONFIG_PROD` | Kubernetes 설정 (프로덕션) | base64 인코딩 |
| `SLACK_WEBHOOK_URL` | Slack 알림 | `https://hooks.slack.com/...` |
| `SONAR_TOKEN` | SonarQube 토큰 | `***` (선택) |

### 3.2 환경 변수 (.env 파일)

| 환경 | 변수 | 값 |
|------|------|-----|
| staging | NODE_ENV | test |
| staging | DATABASE_PATH | /staging/backtest.db |
| staging | LOG_LEVEL | debug |
| production | NODE_ENV | production |
| production | DATABASE_PATH | /prod/backtest.db |
| production | LOG_LEVEL | info |

---

## 4. 파이프라인 실행 시나리오

### 4.1 일반 개발 (develop 브랜치)

```
User: git push origin develop

→ STAGE 1: Build & Lint (3분)
  ✓ 성공

→ STAGE 2: Test (10분)
  ✓ 테스트 통과 (50/51)
  ⚠️ 커버리지 82% (목표: 80%)

→ STAGE 3: Quality (5분)
  ✓ npm audit 경고 없음

→ STAGE 4: Docker Build (8분)
  ✓ 이미지 빌드 & 푸시 (develop 태그)

→ STAGE 5: Deploy to Staging (5분)
  ✓ Smoke 테스트 통과
  ✓ GET /api/health 200 OK

결과: ✅ 배포 성공 (staging)
소요 시간: ~31분
```

### 4.2 릴리스 (v* 태그)

```
User: git tag v2.0.0 && git push origin v2.0.0

→ STAGE 1-4: 동일 (27분)

→ STAGE 5: 스킵 (프로덕션만 배포)

→ STAGE 6: Deploy to Production (10분)
  ✓ Blue-Green 배포 시작
  ✓ Green (v2.0.0) 배포
  ✓ DB 마이그레이션 완료
  ✓ 헬스 체크 통과 (60/60)
  ✓ 트래픽 전환 완료
  ✓ Smoke 테스트 통과

결과: ✅ 프로덕션 배포 성공
배포 방식: Blue-Green (무중단)
롤백 준비: Blue 대기 (24시간)
```

### 4.3 테스트 실패

```
User: git push origin develop (테스트 실패 코드)

→ STAGE 1: Build & Lint
  ✓ 성공

→ STAGE 2: Test
  ❌ 테스트 2개 실패 (50/51)

결과: ❌ 파이프라인 중단
다음 단계: 건너뜀 (STAGE 3, 4, 5)
알림: Slack 채널 #dev-deployments
해결책: 로컬에서 테스트 수정 → 재push
```

---

## 5. 설정 및 설치

### 5.1 GitHub Actions 설정

1. 저장소에 `.github/workflows/build-deploy.yml` 업로드
2. Settings → Secrets and variables → Actions에서 Secrets 추가
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`
   - `SLACK_WEBHOOK_URL`
3. Actions 탭에서 파이프라인 활성화 확인

### 5.2 Docker Registry 설정

**Docker Hub**:
```bash
# 1. Docker Hub 계정 로그인
docker login

# 2. 저장소 생성
# Web: https://hub.docker.com/repository/create
# 저장소: privatetrade/backtesting-simulator

# 3. 로컬 테스트
docker build -t docker.io/privatetrade/backtesting-simulator:latest .
docker push docker.io/privatetrade/backtesting-simulator:latest
```

**GitLab Container Registry** (대안):
```bash
# .gitlab-ci.yml에서 수정
registry: registry.gitlab.com
image: registry.gitlab.com/privatetrade/backtesting-simulator:latest
```

### 5.3 배포 환경 설정

**Staging**:
```bash
# docker-compose-staging.yml 사용
docker-compose -f docker-compose-staging.yml up -d

# 또는 Kubernetes
kubectl apply -f k8s/staging/
```

**Production**:
```bash
# Blue-Green 배포 스크립트
bash scripts/deploy-blue-green.sh v2.0.0

# 또는 Helm
helm upgrade privatetrade-prod ./charts/privatetrade \
  --values values-prod.yaml \
  --set image.tag=v2.0.0
```

---

## 6. 모니터링 및 알림

### 6.1 실시간 모니터링

| 채널 | 알림 대상 | 트리거 |
|------|----------|--------|
| Slack #dev-builds | 개발팀 | 빌드 실패 |
| Slack #dev-tests | 개발팀 | 테스트 실패 (> 5개) |
| Slack #dev-deployments | DevOps팀 | 배포 성공/실패 |
| Email | Lead 개발자 | 프로덕션 배포 |

### 6.2 슬랙 메시지 예시

```
❌ Build Failed
Repository: privatetrade
Branch: develop
Commit: abc123 (short commit hash)
Author: devA@company.com
Message: Add new feature XYZ

Error:
  npm run build failed
  → src/services/BacktestEngine.ts:145:20
  → Property 'xyz' does not exist

Action Required:
  ▸ Fix build error locally
  ▸ git push origin develop
```

---

## 7. 성능 지표

### 7.1 파이프라인 시간 분할

| 단계 | 시간 | 누적 |
|------|------|------|
| Build & Lint | 3분 | 3분 |
| Test | 10분 | 13분 |
| Quality | 5분 | 18분 |
| Docker Build | 8분 | 26분 |
| Deploy (스테이징) | 5분 | 31분 |
| Deploy (프로덕션) | 10분 | 41분 |

**최적화 목표**:
- Docker 빌드: 캐싱으로 8분 → 3분 감소
- 테스트 병렬화: 10분 → 5분 감소

### 7.2 성공률 및 안정성

```
목표:
- 파이프라인 성공률: ≥ 95%
- 배포 성공률: 100% (롤백 포함)
- 복구 시간: < 5분 (롤백)
- 가용성: 99.9%
```

---

## 8. 트러블슈팅

### 8.1 Docker 빌드 실패

```
[오류]
Error: docker build failed: dockerfile syntax error

[해결]
1. 로컬에서 dockerfile 검증
   docker build -t test:latest .
2. BuildKit 비활성화
   DOCKER_BUILDKIT=0 docker build ...
3. 디버깅 모드
   docker build --progress=plain -t test:latest .
```

### 8.2 테스트 타임아웃

```
[오류]
Test timeout after 30000ms

[해결]
1. 테스트 타임아웃 증가 (.github/workflows/build-deploy.yml)
   timeout-minutes: 20 → 30
2. 데이터베이스 연결 확인
3. mock-api 서비스 헬스 체크
```

### 8.3 배포 실패 및 롤백

```
[시나리오]
Green 배포 후 헬스 체크 실패

[자동 롤백]
1. 감지: health check fail (60일 중 0 성공)
2. 트리거: 자동 롤백 스크립트 실행
3. 롤백: LB → Blue로 트래픽 복구
4. 정리: Green 인스턴스 종료
5. 분석: RCA 작성 (오류 원인, 해결책)
```

---

## 9. 정책 및 베스트 프랙티스

### 9.1 배포 정책

| 정책 | 내용 |
|------|------|
| **배포 승인** | 자동 (모든 테스트 통과 시) / 수동 (프로덕션) |
| **배포 시간** | 업무 시간 (9:00-18:00) 권장 |
| **배포 전** | 릴리스 노트, CHANGELOG 준비 |
| **배포 후** | 24시간 모니터링, Blue 유지 |
| **긴급 배포** | Hotfix 브랜치 → Fast-track 배포 |

### 9.2 버전 관리

**SemanticVersioning**: Major.Minor.Patch

```
v2.0.0  : Major (아키텍처 변경)
v2.1.0  : Minor (신규 기능)
v2.0.1  : Patch (버그 수정)
```

---

## 10. 체크리스트

CI/CD 파이프라인 설정 완료 확인:

- [ ] `.github/workflows/build-deploy.yml` 작성
- [ ] GitHub Secrets 설정 (4개 이상)
- [ ] Docker Hub 저장소 생성
- [ ] npm scripts 확인 (build, test, lint)
- [ ] 데이터베이스 마이그레이션 스크립트 준비
- [ ] Smoke 테스트 API 엔드포인트 확인
- [ ] Slack 웹훅 설정
- [ ] 스테이징 환경 구성 확인
- [ ] 프로덕션 환경 구성 및 백업 확인
- [ ] 롤백 계획 문서화
- [ ] 팀 교육 (배포 프로세스)

---

**작성자**: CI/CD_담당자  
**최종 수정**: 2026-02-08  
**버전**: 1.0
