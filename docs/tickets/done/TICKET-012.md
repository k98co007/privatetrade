# TICKET-012: LLD 테스트 환경 구축 (특정 종목 선택 기능)

**상태**: todo  
**우선순위**: P1 HIGH  
**기반**: TICKET-009 (LLD 2.0)  
**선행 조건**: TICKET-009 완료  
**산출물**: 
  - docker-compose-test.yml
  - test-data/mock-stocks.json
  - docs/test/lld/test-environment-setup.md  
**버전**: 2.0  

## 작업 설명
LLD 2.0 기반 테스트 환경 구축. 로컬 테스트 DB, Mock API 서버, 테스트 데이터 세트 구성.

## 환경 구성 요소
1. **테스트 데이터베이스**
   - SQLite (in-memory 또는 파일) with stock_mode, selected_specific_stocks 필드
   - 마이그레이션 스크립트 자동 실행

2. **백엔드 테스트 서버**
   - localhost:8000 (개발 환경과 동일)
   - 4개 신규 API 엔드포인트 활성화
   - 로깅 활성화 (test 레벨)

3. **Mock 데이터**
   - KOSPI 200 종목 코드 100개 (가축)
   - 블랙/화이트리스트 샘플 데이터
   - 테스트 케이스별 시나리오 데이터

4. **테스트 도구**
   - Jest (단위/통합 테스트)
   - Postman 컬렉션 (API 테스트)
   - Selenium (UI 테스트, 선택 사항)

## 수락 기준
- [ ] docker-compose-test.yml 작성 및 테스트
- [ ] 테스트 데이터베이스 마이그레이션 적용 확인
- [ ] 4개 API 엔드포인트 정상 응답 확인
- [ ] 백엔드 로그 기록 확인
- [ ] 테스트 데이터 제공 및 문서화
- [ ] 테스트 실행 가이드 작성 (TICKET-011과 연동)
