# TICKET-010: 코드 개발 (특정 종목 선택 기능)

**상태**: todo  
**우선순위**: P1 HIGH  
**기반**: TICKET-009 (LLD 2.0)  
**선행 조건**: TICKET-009 완료  
**산출물**: 
  - backend/src/components/SpecificStockFilter.js
  - backend/api/routes/stock-selection.js
  - frontend/pages/specific-stock-selection.html
  - 빌드 로그 & 번들 결과  
**버전**: 2.0  

## 작업 설명
LLD 2.0에 기반하여 특정 종목 선택 기능을 구현. Node.js 백엔드 + Vanilla JS 프론트엔드.

### 개발 항목
1. **백엔드 API** (3개 엔드포인트):
   - `POST /api/stocks/specific-select` - 특정 종목 추가
   - `GET /api/stocks/specific-selected` - 선택된 종목 조회
   - `DELETE /api/stocks/specific-select/{code}` - 특정 종목 제거

2. **프론트엔드 UI**:
   - 특정 종목 선택 탭/섹션
   - 종목 검색 & 추가 블록
   - 선택된 종목 목록 & 제거 버튼

3. **통합 테스트**:
   - 단일 종목 선택 시 백테스팅 정상 동작 확인
   - 다중 종목 선택 시 병렬 처리 확인
   - 기존 코스피 200 모드와 특정 종목 모드 전환 확인

## 수락 기준
- [ ] 코드 작성 완료 (PR 제시)
- [ ] 빌드 성공 (npm run build 성공)
- [ ] 3개 엔드포인트 구현 및 로깅
- [ ] 프론트엔드 UI 구현 (Bootstrap 반응형)
- [ ] 단위 테스트 (선택 사항이나 권장)
- [ ] 코드 리뷰 승인
- [ ] Version 2.0 번호 부여
- [ ] 패키징 및 배포 준비 완료
