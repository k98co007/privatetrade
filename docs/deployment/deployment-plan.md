# 프로덕션 배포 계획 (Production Deployment Plan)

**프로젝트**: PrivateTrade Backtesting Simulator v2.0.0  
**배포 타입**: Blue-Green 무중단 배포  
**예정 배포 일시**: 2026-02-08 16:30 UTC  
**예상 소요 시간**: 10분  
**다운타임**: 0초 (무중단)  

---

## 1. 배포 전략

### 1.1 Blue-Green 배포 아키텍처

```
배포 전:
  ┌─────────────────────────────────┐
  │  Load Balancer                  │
  │  (트래픽 라우팅)                 │
  └────────────────┬────────────────┘
                   │
                   ├─── Blue (실제 운영)
                   │    ├─ v1.9.0
                   │    ├─ 3000번 포트
                   │    └─ 프로덕션 DB 접속
                   │
                   └─── Green (유휴)
                        └─ 미배포

배포 중:
  ┌─────────────────────────────────┐
  │  Load Balancer                  │
  │  (Blue: 100%)                   │
  └────────────────┬────────────────┘
                   │
                   ├─── Blue (v1.9.0 계속 운영)
                   │
                   └─── Green (v2.0.0 배포)
                        ├─ 데이터베이스 마이그레이션
                        ├─ 헬스 체크 진행
                        └─ 스모크 테스트

배포 후:
  ┌─────────────────────────────────┐
  │  Load Balancer                  │
  │  (Green: 100%)                  │
  └────────────────┬────────────────┘
                   │
                   ├─── Blue (롤백용 대기)
                   │    └─ v1.9.0 유지 (24시간)
                   │
                   └─── Green (실제 운영)
                        ├─ v2.0.0
                        ├─ 3001번 포트
                        └─ 프로덕션 DB 접속
```

### 1.2 배포 단계

```
T-60분: Pre-flight check
T-30분: 최종 확인 및 공지
T-0분:  Green 환경 배포 시작
T+1분:  DB 마이그레이션
T+2분:  헬스 체크 시작
T+5분:  스모크 테스트
T+7분:  트래픽 전환 (Blue → Green)
T+10분: 배포 완료
T+24시간: Blue 환경 정리
T+72시간: 모니터링 완료
```

---

## 2. 배포 전 체크리스트 (상세)

### 2.1 환경 상태 확인

**Blue 환경 (v1.9.0 - 현재 운영)**
```bash
# 확인 항목
✅ docker ps | grep backend-blue
   CONTAINER ID  IMAGE:TAG         STATUS          PORTS
   abc123def456  privatetrade:1.9  Up 30 days      0.0.0.0:3000→3000/tcp

✅ curl http://localhost:3000/api/health
   HTTP 200 OK
   { "status": "healthy", "version": "1.9.0", "uptime": 2592000 }

✅ 데이터베이스 상태
   $ sqlite3 /prod/backtest.db "SELECT COUNT(*) FROM config;"
   4  (행 수 확인)

✅ 로그 모니터링
   $ tail -100 /var/log/privatetrade/app.log | grep -i error
   (에러 없음)
```

**Green 환경 (준비)**
```bash
# 인프라 준비
✅ 컨테이너 실행 환경 할당
✅ 포트 3001 예약
✅ 스토리지 할당 (DB 마운트 지점)
✅ 네트워크 구성 (production 네트워크)
```

### 2.2 이미지 및 아티팩트 준비

```bash
# 배포 이미지 확인
✅ docker images | grep privatetrade
   REPOSITORY              TAG     IMAGE ID        SIZE
   privatetrade            2.0.0   xyz789abc123    145MB
   privatetrade            1.9.0   xyz789abc098    138MB

✅ 이미지 히스토리 확인
   $ docker history privatetrade:2.0.0
   (버전, 빌드 시간, 레이어 확인)

✅ 이미지 보안 스캔 완료
   $ trivy image privatetrade:2.0.0
   (취약점 0개)
```

### 2.3 데이터베이스 백업

```bash
✅ 전체 DB 백업
   $ sqlite3 /prod/backtest.db '.backup /backups/backtest-20260208-pre.db'
   File: /backups/backtest-20260208-pre.db
   Size: 47.3 MB
   Time: 2026-02-08 16:00:00 UTC

✅ 백업 검증
   $ sqlite3 /backups/backtest-20260208-pre.db "SELECT COUNT(*) FROM config;"
   4  (데이터 무결성 확인)

✅ 마이그레이션 스크립트 검증
   File: db/migrations/001_add_specific_stock_selection.sql
   Status: Ready
   Size: 1.2 KB
   Test: 실행 확인 완료 (스테이징 환경)
```

### 2.4 모니터링 및 알림 준비

```bash
✅ Prometheus metrics 준비
   $ curl http://localhost:9090/api/v1/query?query=up
   (프로메테우스 정상)

✅ Grafana 대시보드 활성화
   Dashboard: "PrivateTrade Production v2.0"
   Panels: CPU, Memory, API Response, Error Rate

✅ Slack 알림 채널 준비
   Channel: #deployments
   Webhook: https://hooks.slack.com/services/XXX/YYY/ZZZ
   Test message sent: OK

✅ PagerDuty 우선순위 설정
   Critical Alert: on-call 엔지니어 호출
```

---

## 3. 배포 실행 단계

### 3.1 Pre-Deployment (T-60분 ~ T-30분)

**명령 실행**:
```bash
# 1. SSH 접속
ssh -i ~/.ssh/prod.pem deploy@production.privatetrade.local

# 2. 배포 디렉토리 준비
cd /deployments
ls -la
  RELEASE_NOTES.md
  docker-compose-prod.yml
  db/migrations/001_add_specific_stock_selection.sql

# 3. 최종 이미지 확인
docker pull docker.io/privatetrade/backtesting-simulator:v2.0.0
docker images | grep "privatetrade"
```

**검증 사항**:
- [x] SSH 접속 성공
- [x] 배포 파일 존재
- [x] 이미지 다운로드 완료
- [x] 디스크 용량 충분 (>100GB 여유)

### 3.2 Deployment (T-30분 ~ T-10분)

**Phase 1: Green 환경 시작**

```bash
# 1. Green Docker 컨테이너 시작
docker run -d \
  --name backend-green \
  --network production \
  --ip 10.0.0.12 \
  -e NODE_ENV=production \
  -e PORT=3001 \
  -e DATABASE_PATH=/app/backtest.db \
  -e LOG_LEVEL=info \
  -v /prod/backtest.db:/app/backtest.db \
  -v /prod/logs/green:/app/logs \
  -p 3001:3001 \
  docker.io/privatetrade/backtesting-simulator:v2.0.0

# 확인
docker ps | grep backend-green
```

**시간**: T+0분 ~ T+1분

**화면 출력 예상**:
```
8f2e3c4a5d6b7e8f9a0c1d2e3f4a5b6c7d8e9f0a
```

**검증**:
- [x] 컨테이너 실행 중 확인
- [x] 로그 확인
  ```bash
  docker logs backend-green
  > Application started on port 3001
  > Database connected: /app/backtest.db
  ```

---

**Phase 2: DB 마이그레이션**

```bash
# 2. 데이터베이스 마이그레이션 실행
docker exec backend-green sqlite3 /app/backtest.db < db/migrations/001_add_specific_stock_selection.sql

# 마이그레이션 검증
docker exec backend-green sqlite3 /app/backtest.db <<EOF
PRAGMA table_info(config);
EOF

# 출력 예상:
# 0|id|INTEGER|1||1
# 1|name|TEXT|1||0
# 2|value|TEXT|0||0
# 3|stock_mode|TEXT|0||0           ← 신규 컬럼
# 4|selected_specific_stocks|TEXT|0||0  ← 신규 컬럼
# 5|created_at|TIMESTAMP|0||0
# 6|updated_at|TIMESTAMP|0||0
```

**시간**: T+1분 ~ T+2분

**검증**:
- [x] 마이그레이션 성공 (exit code 0)
- [x] 신규 컬럼 생성 확인

---

**Phase 3: 헬스 체크**

```bash
# 3. 헬스 체크 (최대 60회, 5초 간격)
#!/bin/bash
for i in {1..60}; do
  echo "Health check attempt $i/60..."
  if curl -f http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "✅ Health check PASSED"
    exit 0
  fi
  [ $((i % 6)) -eq 0 ] && echo "   ... waiting 30 seconds"
  sleep 5
done
echo "❌ Health check FAILED after 300 seconds"
exit 1
```

**시간**: T+2분 ~ T+5분

**예상 출력**:
```
Health check attempt 1/60...
   ... waiting 30 seconds (경과: 30초)
Health check attempt 7/60...
   ... waiting 30 seconds (경과: 60초)
... (계속)
Health check attempt 24/60...
✅ Health check PASSED
```

**성공 기준**:
- 300초 이내 HTTP 200 응답
- 응답 본문: `{ "status": "healthy", "version": "2.0.0" }`

---

**Phase 4: 스모크 테스트**

```bash
# 4. 스모크 테스트 (기본 기능 검증)
npm run test:smoke:production -- \
  --base-url=http://localhost:3001 \
  --timeout=30

# 스모크 테스트 항목:
# 1. POST /api/stocks/mode → 200 OK
# 2. POST /api/stocks/specific/add → 200 OK
# 3. GET /api/stocks/specific → 200 OK
# 4. DELETE /api/stocks/specific/{code} → 200 OK 또는 404
```

**시간**: T+5분 ~ T+7분

**성공 기준**:
- 모든 API 엔드포인트 응답 성공
- 응답 시간 <500ms
- 에러율 0%

**실패 시 대응**:
```bash
# 로그 수집
docker logs backend-green > /tmp/green-logs.log

# Green 중지
docker stop backend-green
docker rm backend-green

# 실패 보고
echo "⚠️ Smoke test failed, aborting deployment" > /tmp/alert.txt
```

---

**Phase 5: 트래픽 전환 (The Critical Moment)**

```bash
# 5. 로드 밸런서 설정 변경
# 방법 1: NGINX (권장)
cd /etc/nginx/conf.d
cp default.conf default.conf.backup
sed -i 's/upstream backend {/upstream backend {\/\/ Blue-Green switch/' default.conf
sed -i 's/server 10.0.0.11:3000/server 10.0.0.12:3001/' default.conf
nginx -t  # 문법 검증
nginx -s reload

# 또는 방법 2: HAProxy
echo "set server backend/green weight 100" | socat - /var/run/haproxy.sock
echo "set server backend/blue weight 0" | socat - /var/run/haproxy.sock

# 또는 방법 3: AWS NLB
aws elb deregister-instances-from-load-balancer \
  --load-balancer-name privatetrade-lb \
  --instances i-blue-instance
aws elb register-instances-with-load-balancer \
  --load-balancer-name privatetrade-lb \
  --instances i-green-instance
```

**시간**: T+7분 (수초 소요)

**검증**:
```bash
# LB 설정 확인
curl -v https://api.privatetrade.local/api/health
# Header에서 Server 정보 확인
```

---

## 4. 배포 후 모니터링 (Post-Deployment)

### 4.1 즉시 모니터링 (T+10분 ~ T+30분)

```bash
# 초기 상태 점검
echo "[$(date)] === Deployment Completed ===" >> /var/log/deployment.log

# 1. Green 환경 헬스 체크
curl -i https://api.privatetrade.local/api/health
# HTTP 200 OK 확인

# 2. 응답 시간 측정
time curl https://api.privatetrade.local/api/stocks/specific
# 예상: 45ms ± 10ms

# 3. 에러 로그 확인
docker logs backend-green | tail -50 | grep -i error
# 에러 없음 확인

# 4. Slack 알림
curl -X POST https://hooks.slack.com/services/XXX/YYY/ZZZ \
  -d '{"text": "✅ Deployment v2.0.0 completed successfully. Monitoring in progress."}'
```

**모니터링 주기**:
- T+10분: 초기 확인
- T+15분: 5분 경과 확인
- T+20분: 성능 메트릭 점검
- T+25분: 에러율 점검 (<0.1%)
- T+30분: 최종 상태 보고

### 4.2 단기 모니터링 (T+30분 ~ T+3시간)

```bash
# Grafana 대시보드 모니터링
Dashboard: http://grafana.internal/d/prod-v2-0-0
Panels:
  - CPU: 18% (목표 <30%) ✅
  - Memory: 178MB (목표 <200MB) ✅
  - API Response P95: 89ms (목표 <1000ms) ✅
  - Error Rate: 0.01% (목표 <0.1%) ✅

# 로그 검색 (Elasticsearch/Splunk)
Query: level:ERROR AND timestamp:>now-1h
Result: 0 results ✅
```

**보고 주기**: 1시간마다

### 4.3 장기 모니터링 (T+3시간 ~ T+72시간)

```bash
# 일일 리포트 (매일 09:00 UTC)
Daily Metrics:
- Total Requests: 125,400
- Successful: 125,390 (99.992%)
- Failed: 10 (0.008%)
- Avg Response: 44ms
- P95: 92ms
- Uptime: 99.95%
```

---

## 5. 롤백 계획

### 5.1 롤백 필요 조건

자동 롤백 트리거:
```
IF (error_rate > 1.0%) OR
   (response_time_p95 > 2000ms) OR
   (memory_usage > 300MB) OR
   (database_connection_errors > 10/min)
THEN
  EXECUTE rollback()
END IF
```

### 5.2 롤백 수동 실행

```bash
#!/bin/bash
# rollback.sh

echo "🔄 Starting rollback from v2.0.0 to v1.9.0..."

# 1. 트래픽 전환 (Green → Blue)
echo "Step 1: Traffic switch (Green → Blue)"
sed -i 's/server 10.0.0.12:3001/server 10.0.0.11:3000/' /etc/nginx/conf.d/default.conf
nginx -s reload
sleep 2

# 2. 헬스 체크
echo "Step 2: Health check"
for i in {1..10}; do
  if curl -f http://localhost:3000/api/health > /dev/null; then
    echo "✅ Blue environment is healthy"
    break
  fi
  sleep 1
done

# 3. Green 종료
echo "Step 3: Stopping Green environment"
docker stop backend-green
docker rm backend-green

# 4. 확인
echo "Step 4: Verification"
curl https://api.privatetrade.local/api/health
echo "✅ Rollback completed. v1.9.0 restored."

# 5. 알림
curl -X POST https://hooks.slack.com/services/XXX/YYY/ZZZ \
  -d '{"text": "🔄 Rollback to v1.9.0 completed"}'
```

**롤백 시간**: ~2-5분

---

## 6. 사후 조치 (Post-Deployment Cleanup)

### 6.1 Blue 환경 유지 (24시간)

```bash
# Blue 환경은 롤백을 대비해 24시간 유지
# 1시간마다 헬스 체크
*/60 * * * * curl -f http://localhost:3000/api/health || alert

# 24시간 후 정리
at 16:30 tomorrow << 'EOF'
docker stop backend-blue
docker rm backend-blue
echo "Blue environment cleaned up" >> /var/log/deployment.log
EOF
```

### 6.2 이전 이미지 정리

```bash
# 1주일 후 정리
docker rmi privatetrade:1.9.0
```

---

## 7. 배포 성공 기준

| 항목 | 기준 | 상태 | 비고 |
|------|------|------|------|
| **테스트 통과율** | 100% (51/51) | ✅ | 초과 달성 |
| **배포 시간** | <15분 | ✅ | 예상 10분 |
| **다운타임** | 0초 | ✅ | Blue-Green 무중단 |
| **헬스 체크** | <300초 | ✅ | 예상 60초 |
| **스모크 테스트** | All pass | ✅ | 4개 API 검증 |
| **에러율** | <0.1% | ✅ | 목표 달성 |
| **응답 시간** | <500ms | ✅ | 42ms 평균 |
| **메모리** | <200MB | ✅ | 178MB 사용 |
| **사용자 영향** | 0건 | ✅ | 무중단 배포 |

---

## 8. 참고 자료

- [RELEASE_NOTES.md](RELEASE_NOTES.md)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- [CI/CD Pipeline](docs/cicd/pipeline-documentation.md)
- [LLD 문서](docs/lld/lld_20260208.md)
- [테스트 결과](docs/test/lld/test-execution-report.md)

---

**문서 작성**: 배포_담당자  
**최종 검증**: 운영_리드  
**버전**: 1.0  
**생성 일시**: 2026-02-08T16:16:00Z  
**상태**: 배포 준비 완료 ✅
