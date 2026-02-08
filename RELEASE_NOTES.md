# RELEASE NOTES v2.0.2 (Hotfix)

**릴리스 일자**: 2026년 2월 9일  
**배포 대상**: Production  
**배포 방식**: Blue-Green (무중단 배포)  
**배포 예상 소요시간**: 5분  

---

## 1. 주요 변경사항

### v2.0.2 (Hotfix - Patch Version)

**버그 수정**:
- ✅ [TICKET-028] 백테스트 결과 다운로드 엔드포인트 404 에러 수정
  - 프론트엔드가 올바른 백엔드 엔드포인트 호출 (`/api/backtest/result/:id`)
  - 다운로드 기능 정상 작동

**파일 변경**:
- `frontend/pages/specific-stock-selection.html` (다운로드 함수 수정)
- 백엔드 변경 없음

**테스트 결과**:
- Code verification: 26/26 항목 ✅
- Integration tests: ✅ 통과
- Regression tests: ✅ 통과

---

## 2. 이전 릴리스 (v2.0.1)

### v2.0.1 (Bug Fix Release - Patch Version)

**버그 수정**:
- 🐛 [TICKET-023] 프론트엔드 백테스트 결과 미표시 버그 수정
  - 백테스트 진행 상황 실시간 표시 기능 추가
  - 5개 성과 지표 (수익률, 샤프지수, 최대손실률, 거래횟수, 승률) 표시 기능 추가
  - UI 개선: 진행 바 + 결과 테이블 추가
  - 에러 처리 강화: 타임아웃 (30분) + 재시도 로직 (최대 3회)

**파일 변경**:
- `frontend/pages/specific-stock-selection.html` (+383줄)

**테스트 결과**:
- 테스트 통과: 5/5 TC (TICKET-024, TICKET-026)
- 버그 발견: 0개
- 배포 승인: ✅ 획득

---

## 2. 이전 릴리스 (v2.0.0)

### v2.0.0 (New Feature Release - Minor Version)

**주요 신규 기능**:
- ✨ **특정 종목 선택 기능**: 사용자가 관심 종목을 개별 선택하여 백테스트 가능
- ✨ **3가지 모드 지원**: All (전체), Filtered (필터링), Specific (특정 선택)
- ✨ **CI/CD 파이프라인**: 자동 빌드/테스트/배포 시스템 구축
- ✨ **나머지 성능 최적화**: 100개 종목 1.8초 로드 (목표 2초)

**개선 사항**:
- 🔧 API 응답 시간 단축 (평균 42ms)
- 🔧 코드 커버리지 향상 (89%)
- 🔧 메모리 사용 최적화 (178MB)

---

## 2. 기술 상세

### 2.1 신규 API 엔드포인트 (4개)

```
POST /api/stocks/mode
  내용: 종목 선택 모드 변경
  예: { mode: "specific", stocks: ["005930", "000660"] }
  
POST /api/stocks/specific/add
  내용: 특정 종목 추가 (최대 100개)
  예: { codes: ["005930", "000660", "034020"] }
  
GET /api/stocks/specific
  내용: 현재 선택된 종목 조회
  응답: { stocks: [...], total: 3 }
  
DELETE /api/stocks/specific/{code}
  내용: 특정 종목 삭제
  응답: { deleted: 1, remaining: 2 }
```

### 2.2 데이터베이스 스키마 변경

**신규 컬럼**:
- `stock_mode` (TEXT): 'all' | 'filtered' | 'specific'
- `selected_specific_stocks` (TEXT): JSON 문자열로 선택된 종목 코드 저장

**마이그레이션 스크립트**: `db/migrations/001_add_specific_stock_selection.sql`
- 자동 생성 및 적용 (배포 시 실행)
- 기존 데이터 호환성 유지

### 2.3 시스템 아키텍처 개선

```
Before (v1.0)              After (v2.0)
─────────────────          ─────────────────────────
UI                         UI (BacktestUI)
 └─ API Routes              └─ API Routes
     ├─ Config               ├─ Config Repository
     └─ Data Manager         ├─ Stock Filter (NEW!)
                             ├─ Data Manager
                             └─ Backtest Engine

신규 컴포넌트: StockFilter
- 역할: 3가지 모드 기반 종목 필터링
- 메소드: applyFilter(), applyBlackWhiteFilter(), applySpecificFilter()
- 성능: 100개 종목 필터링 <2초
```

---

## 3. 테스트 결과 요약

| 테스트 항목 | 결과 | 상태 |
|-----------|------|------|
| **API 테스트** | 30/30 통과 | ✅ |
| **UI 테스트** | 10/10 통과 | ✅ |
| **통합 테스트** | 10/10 통과 | ✅ |
| **성능 테스트** | 1/1 통과 | ✅ |
| **전체** | 51/51 통과 | ✅ |
| **커버리지** | 89% | ✅ 목표 80% 달성 |
| **성능** | 1.8초 (100개) | ✅ 목표 2초 달성 |

---

## 4. 배포 전 체크리스트

### 4.1 기술 검증
- [x] 모든 자동화 테스트 통과 (51/51)
- [x] 코드 리뷰 완료 (4개 모듈)
- [x] 보안 검사 완료 (npm audit, SAST)
- [x] 성능 테스트 통과 (벤치마크 기준)
- [x] DB 마이그레이션 테스트 완료
- [x] CI/CD 파이프라인 검증 완료

### 4.2 배포 준비
- [x] 배포 승인 획득
- [x] 운영 팀 공지
- [x] 롤백 계획 수립
- [x] 모니터링 알림 설정
- [x] RELEASE_NOTES.md 작성 ← **현재 문서**
- [ ] 배포 실행 (TICKET-015)

### 4.3 사후 조치
- [ ] 배포 완료 후 모니터링 (24시간)
- [ ] 사용자 피드백 수집
- [ ] 성능 메트릭 확인
- [ ] 버그 리포트 접수
- [ ] 블루 환경 유지 (24시간)

---

## 5. 배포 롤백 계획

### 5.1 롤백 조건

```
배포 후 다음 중 하나 발생 시 즉시 롤백:
- 심각 오류 (500 에러) 발생률 > 1%
- API 응답 시간 > 1초
- 메모리 사용 > 300MB
- CPU 사용률 > 60%
- 데이터 무결성 문제
- 사용자 보고: "사용 불가"
```

### 5.2 롤백 실행

```bash
# 1. LB 트래픽 전환 (Blue로)
traffic-switch --from=green --to=blue

# 2. Green 서비스 종료
docker stop backend-green
docker rm backend-green

# 3. 검증
curl http://api.privatetrade.local/health

# 4. 통보
slack-notify "#deployments" "Rollback completed, v1.9.0 restored"
```

**롤백 시간**: ~2분

---

## 6. 버전 관리 정책

**Semantic Versioning**: Major.Minor.Patch

| 버전 | 변경 유형 | 예시 |
|------|---------|------|
| Major | 아키텍처/API 호환 불가 변경 | 1.0.0 → 2.0.0 |
| Minor | 신규 기능 추가 (역호환) | 1.0.0 → 1.1.0 |
| Patch | 버그 수정 | 1.0.1 → 1.0.2 |

**현재 버전**: 2.0.0 (신규 기능 추가)

---

## 7. 성능 비교 (v1.9.0 vs v2.0.0)

| 지표 | v1.9.0 | v2.0.0 | 변화 |
|------|--------|--------|------|
| 로드 시간 (100개) | 2.1초 | 1.8초 | ⬇️ 14% 개선 |
| API 응답 | 48ms | 42ms | ⬇️ 13% 개선 |
| 메모리 | 195MB | 178MB | ⬇️ 9% 개선 |
| 코드 커버리지 | 84% | 89% | ⬆️ 5% 향상 |

---

## 8. 호환성 정보

### 8.1 브라우저 호환성

| 브라우저 | v1.9.0 | v2.0.0 |
|---------|--------|--------|
| Chrome 90+ | ✅ | ✅ |
| Firefox 88+ | ✅ | ✅ |
| Safari 14+ | ✅ | ✅ |
| Edge 90+ | ✅ | ✅ |
| IE 11 | ⚠️ 지원 중단 | ❌ |

### 8.2 API 호환성

✅ **역호환성 유지**
- 기존 API 엔드포인트 모두 작동
- 신규 엔드포인트 추가 (4개)
- 요청/응답 형식 동일

⚠️ **주의사항**
- 신규 컬럼 (`stock_mode`, `selected_specific_stocks`) 추가
- 기존 데이터 마이그레이션 자동 실행
- DB 백업 권장 (자동 수행)

---

## 9. 알려진 문제 및 제한사항

### 9.1 알려진 문제: 없음 ✅

모든 테스트 통과, 심각한 버그 발견 안 됨

### 9.2 제한사항

| 제한 | 세부 | 완화책 |
|------|------|--------|
| 최대 선택 종목 | 100개 | v2.1에서 500개로 증가 예정 |
| 동시 사용자 | 1000명 | 부하 분산기 추가로 5000명까지 확장 가능 |
| 캐시 TTL | 고정 60초 | 설정 가능하게 개선 (v2.1) |

---

## 10. 향후 계획

### v2.1 (예상 1개월)
- 최대 선택 종목 500개 지원
- 캐시 정책 커스터마이징
- UI 로딩 애니메이션 개선

### v3.0 (예상 3개월)
- 고급 필터링 (종목별 가중치)
- 포트폴리오 저장 및 로드
- 다국어 지원 (한문/영문/일문)

---

## 11. 지원 및 문의

**문제 보고**: https://github.com/privatetrade/issues  
**이메일**: support@privatetrade-dev.local  
**Slack**: #product-releases

---

## 12. 참고 문서

- [배포 계획](deployment-plan.md)
- [CI/CD 파이프라인](../cicd/pipeline-documentation.md)
- [API 문서](../api/README.md)
- [HLD](../hld/hld_20260208.md)
- [LLD](../lld/lld_20260208.md)

---

**작성자**: 배포_담당자  
**검증자**: QA_리드, 개발_리드  
**승인자**: 프로젝트_매니저  
**승인 일시**: 2026-02-08T16:16:00Z
