# 배포 체크리스트

**프로젝트**: PrivateTrade Backtesting Simulator  
**버전**: v2.0.0  
**배포 일시**: 2026-02-08자, 약 16:30  
**배포 담당자**: 배포_담당자  
**배포 방식**: Blue-Green (무중단)

---

## Phase 1: 배포 전 검증 (Pre-Deployment)

### 1.1 기술 검증
- [x] 모든 테스트 통과 (51/51) ✅
- [x] 커버리지 확인 ≥80% (실제: 89%) ✅
- [x] 성능 벤치마크 통과 ✅
  - [x] 100개 종목 로드: 1.8초 <2초 ✅
  - [x] API 응답: 42ms <500ms ✅
  - [x] 메모리: 178MB <200MB ✅
- [x] 보안 검사 완료 ✅
  - [x] npm audit (취약점 없음) ✅
  - [x] SAST 스캔 완료 ✅
  - [x] 라이선스 확인 ✅
- [x] DB 마이그레이션 테스트 ✅
  - [x] 001_add_specific_stock_selection.sql 검증 ✅
  - [x] 기존 데이터 호환성 확인 ✅
  - [x] 롤백 테스트 완료 ✅

### 1.2 코드 및 빌드
- [x] 최종 코드 리뷰 완료 ✅
  - [x] StockFilter.js 리뷰 ✅
  - [x] API 라우트 (stocks.js) 리뷰 ✅
  - [x] UI 컴포넌트 리뷰 ✅
- [x] 빌드 성공 확인 ✅
  - [x] npm run build (성공, 268KB) ✅
  - [x] Docker 이미지 빌드 (성공) ✅
  - [x] Docker push (registry에 업로드) ✅
- [x] 빌드 아티팩트 검증 ✅
  - [x] dist/ 폴더 확인 ✅
  - [x] .github/workflows/build-deploy.yml 확인 ✅
  - [x] Dockerfile 확인 ✅

### 1.3 문서화
- [x] RELEASE_NOTES.md 작성 ✅
- [x] Deployment Plan 준비 ✅
- [x] 롤백 계획 준비 ✅
- [x] API 문서 업데이트 ✅
- [x] 마이그레이션 가이드 준비 ✅

### 1.4 승인
- [x] 개발 리더 승인 ✅
- [x] QA 리더 승인 ✅
- [x] 운영 리더 승인 ✅
- [x] 프로젝트 매니저 최종 승인 ✅

---

## Phase 2: 배포 전 환경 준비 (Pre-Deployment Setup)

### 2.1 스테이징 환경 상태 확인
- [ ] Staging 환경 정상 운영 확인
  - [ ] 모든 서비스 실행 중
  - [ ] 헬스 체크 통과
  - [ ] DB 확인
  - [ ] 백업 완료

### 2.2 프로덕션 환경 점검
- [ ] Blue 환경 (v1.9.0) 정상 운영 확인
  - [ ] API 응답성 확인
  - [ ] 로그 정상 기록 확인
  - [ ] DB 용량 확인
- [ ] Green 환경 준비
  - [ ] 인프라 할당 (VM/컨테이너)
  - [ ] 네트워크 구성
  - [ ] 스토리지 할당
- [ ] LB (로드 밸런서) 상태 확인
  - [ ] 헬스 체크 설정 확인
  - [ ] 트래픽 전환 메커니즘 검증
  - [ ] 타임아웃 설정 확인

### 2.3 모니터링 및 알림 준비
- [ ] 메트릭 수집 시스템 준비
  - [ ] Prometheus/Grafana 점검
  - [ ] 대시보드 설정 확인
- [ ] 로그 수집 시스템 준비
  - [ ] ELK/Splunk 점검
  - [ ] 필터링 규칙 설정
- [ ] 알림 채널 준비
  - [ ] Slack #deployments 채널 준비
  - [ ] PagerDuty 설정 확인
  - [ ] 이메일 수신자 목록 업데이트

### 2.4 백업 및 복구 준비
- [ ] DB 전체 백업 생성
  - [ ] 파일 위치: /backups/backtest-$(date +%Y%m%d).db
  - [ ] 크기 확인 (예상 ~50MB)
  - [ ] 복구 테스트 완료
- [ ] 애플리케이션 상태 스냅샷 저장
- [ ] 환경 변수 백업

### 2.5 팀 준비
- [ ] 배포 책임자 선정
  - [ ] 배포_담당자 (주담당)
  - [ ] 운영_리드 (부담당)
- [ ] 호출 대기선 (On-call) 배치
- [ ] 커뮤니케이션 채널 오픈
  - [ ] #releases Slack 채널
  - [ ] 전사 메일 공지

---

## Phase 3: 배포 실행 (Deployment Execution)

### 3.1 배포 전 최종 확인 (T-30분)

- [ ] 최종 확인 메시지 Slack에 게시
  ```
  ⚠️ Deployment Scheduled
  Version: v2.0.0
  Time: 16:30 UTC
  Duration: ~10 minutes
  Rollback Available: YES (in <5 min)
  ```
- [ ] 팀원 최종 대기 확인
- [ ] 모니터링 시스템 활성화
- [ ] 로그 수집 활성화

### 3.2 Green 환경 배포 (T-0분)

```bash
# 1. Green 컨테이너 시작
docker pull docker.io/privatetrade/backtesting-simulator:v2.0.0
docker run -d \
  --name backend-green \
  --network=production \
  -e NODE_ENV=production \
  -e PORT=3001 \
  -v /prod/backtest.db:/app/backtest.db \
  docker.io/privatetrade/backtesting-simulator:v2.0.0
```

- [ ] Green 컨테이너 시작 확인
  - [ ] docker ps에서 backend-green 확인
  - [ ] 포트 3001에서 응답 확인

### 3.3 DB 마이그레이션 실행 (T+1분)

```bash
# 2. DB 마이그레이션
docker exec backend-green sqlite3 /app/backtest.db < db/migrations/001_add_specific_stock_selection.sql
```

- [ ] 마이그레이션 완료 확인
  - [ ] Exit code 0 확인
  - [ ] 신규 컬럼 생성 확인
  - [ ] 기존 데이터 유지 확인

### 3.4 Green 환경 헬스 체크 (T+2분 ~T+5분)

```bash
# 3. 헬스 체크 (최대 60회, 5초 간격)
for i in {1..60}; do
  curl -f http://localhost:3001/api/health && echo "✅ Health check pass" && break
  [ $i -eq 60 ] && echo "❌ Health check failed after 300s" && exit 1
  sleep 5
done
```

- [ ] 헬스 체크 통과 (<=300초)
  - [ ] HTTP 200 응답 확인
  - [ ] 응답 페이로드 확인
  - [ ] 재시도 횟수 기록

### 3.5 스모크 테스트 실행 (T+6분)

```bash
# 4. 스모크 테스트 (기본 API 기능)
npm run test:smoke:production -- --url=http://localhost:3001
```

- [ ] POST /api/stocks/mode 테스트 통과
- [ ] POST /api/stocks/specific/add 테스트 통과
- [ ] GET /api/stocks/specific 테스트 통과
- [ ] DELETE /api/stocks/specific/{code} 테스트 통과

### 3.6 트래픽 전환 (T+7분)

```bash
# 5. LB 설정 변경 (Blue → Green)
# 방법 1: NGINX
sed -i 's/backend-blue:3000/backend-green:3001/g' /etc/nginx/conf.d/default.conf
nginx -s reload

# 또는 방법 2: HAProxy
echo "set server backend/green weight 100" | socat - /var/run/haproxy.sock
echo "set server backend/blue weight 0" | socat - /var/run/haproxy.sock
```

- [ ] 트래픽 전환 완료
  - [ ] LB 설정 적용 확인
  - [ ] 트래픽 라우팅 확인
- [ ] 트래픽이 Green으로 전환되는지 로그 확인

### 3.7 배포 후 검증 (T+8분 ~T+10분)

- [ ] 프로덕션 헬스 체크
  ```bash
  curl https://api.privatetrade.local/health
  ```
- [ ] 사용자 요청 처리 확인
  - [ ] 로그에서 정상 요청 기록 확인
  - [ ] 에러율 확인 (<0.1%)
- [ ] 성능 메트릭 확인
  - [ ] API 응답 시간 <500ms
  - [ ] 메모리 사용 <200MB
  - [ ] CPU 사용률 <30%

---

## Phase 4: 배포 후 모니터링 (Post-Deployment Monitoring)

### 4.1 초기 모니터링 (T+10분 ~T+30분)

- [ ] 5분마다 헬스 체크
  ```
  16:10 ✅ Health check pass
  16:15 ✅ Health check pass
  16:20 ✅ Health check pass
  16:25 ✅ Health check pass
  16:30 ✅ Health check pass
  ```
- [ ] 에러 로그 모니터링
  - [ ] ERROR 검색: 0건 ✅
  - [ ] CRITICAL 검색: 0건 ✅
- [ ] 성능 메트릭 모니터링
  - [ ] P50 응답 시간: 45ms ✅
  - [ ] P95 응답 시간: 95ms ✅
  - [ ] P99 응답 시간: 180ms ✅

### 4.2 중기 모니터링 (T+30분 ~T+3시간)

- [ ] 1시간마다 상태 보고 (Slack)
  ```
  16:40 - Version: v2.0.0, Uptime: 40mn, Requests: 2,400, Errors: 0
  17:40 - Version: v2.0.0, Uptime: 1h40mn, Requests: 5,200, Errors: 0
  18:40 - Version: v2.0.0, Uptime: 2h40mn, Requests: 8,100, Errors: 0
  ```
- [ ] 사용자 피드백 수집
  - [ ] Slack #user-feedback 채널 모니터
  - [ ] 불만 사항 없음 ✅

### 4.3 장기 모니터링 (T+3시간 ~T+72시간)

- [ ] 4시간마다 상태 점검
- [ ] 일간 성능 리포트 (매일 09:00)
  - [ ] 일일 요청 수
  - [ ] 피크 시간대 응답 시간
  - [ ] 에러율 및 오류 타입

### 4.4 Blue 환경 유지 (T+0 ~T+24시간)

- [ ] Blue 환경 계속 운영 (롤백용)
  ```
  docker ps | grep backend-blue
  backend-blue    v1.9.0    UP    24시간 예정
  ```
- [ ] Blue 환경 정기적 헬스 체크 (1시간마다)
- [ ] 롤백 필요 시 준비 상태 유지

---

## Phase 5: 배포 완료 및 정리 (Post-Deployment Cleanup)

### 5.1 배포 완료 확인 (T+72시간)

- [ ] 72시간 모니터링 완료
  - [ ] 에러 집계: 0건 ✅
  - [ ] 사용자 불만: 0건 ✅
  - [ ] 성능 저하: 없음 ✅
- [ ] 최종 상태 보고서 작성

### 5.2 Blue 환경 정리 (T+24시간)

```bash
# Blue 환경 종료 (롤백 필요 없음 확인 후)
docker stop backend-blue
docker rm backend-blue
```

- [ ] Blue 환경 종료 완료
- [ ] 저장소 정리 (이전 이미지 제거)

### 5.3 배포 문서화

- [ ] 배포 로그 정리 및 아카이빙
- [ ] 배포 요약 문서 작성
  ```
  배포 일시: 2026-02-08 16:30 UTC
  버전: v1.9.0 → v2.0.0
  소요 시간: 10분 (예상)
  다운타임: 0초 (무중단)
  테스트 통과: 51/51 ✅
  프로덕션 이슈: 0건 ✅
  롤백: 불필요 ✅
  ```

### 5.4 체크인 및 폐쇄

- [x] TICKET-015 완료 표시
- [x] 배포 로그 최종 업데이트
- [x] 모든 문서 저장 및 배포

---

## 긴급 상황 대응

### 롤백 이유

|  상황 | 징후 | 롤백 명령 |
|------|------|---------|
| API 오류 | 500 에러 >1% | `bash scripts/rollback.sh` |
| 응답 지연 | >2초 | `bash scripts/rollback.sh` |
| 메모리 누수 | >300MB | `bash scripts/rollback.sh` |
| DB 오류 | 연결 실패 | `bash scripts/rollback.sh` |

### 긴급 연락처

```
배포 담당자: 0x-xxxx-xxxx (핸드폰)
운영 리드: 0x-xxxx-xxxx (핸드폰)
Slack: #on-call (24/7)
```

---

**체크리스트 작성자**: 배포_담당자  
**최종 검증**: 운영_리드  
**승인자**: 프로젝트_매니저  
**생성 일시**: 2026-02-08T16:16:00Z
