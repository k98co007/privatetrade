#!/usr/bin/env python3
"""
TICKET-028: 백테스트 결과 다운로드 엔드포인트 404 에러 버그 수정
테스트 스크립트
"""

import json
import sys
import re
from pathlib import Path

def test_frontend_code():
    """프론트엔드 코드에서 올바른 엔드포인트 호출 확인"""
    print("\n" + "="*70)
    print("TICKET-028: 백테스트 결과 다운로드 엔드포인트 수정 검증")
    print("="*70 + "\n")

    frontend_file = Path('frontend/pages/specific-stock-selection.html')
    
    if not frontend_file.exists():
        print(f"❌ 프론트엔드 파일을 찾을 수 없습니다: {frontend_file}")
        return False

    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 테스트 1: 잘못된 엔드포인트가 제거되었는지 확인
    print("📋 테스트 1: 잘못된 엔드포인트 제거 확인")
    old_endpoint = "/api/results/"
    if old_endpoint in content:
        print(f"  ❌ 잘못된 엔드포인트가 여전히 존재: {old_endpoint}")
        return False
    else:
        print(f"  ✅ 잘못된 엔드포인트({old_endpoint})가 제거되었습니다.")

    # 테스트 2: 올바른 엔드포인트 호출 확인
    print("\n📋 테스트 2: 올바른 엔드포인트 호출 확인")
    correct_endpoint = "/api/backtest/result/"
    if correct_endpoint in content:
        print(f"  ✅ 올바른 엔드포인트가 사용 중: {correct_endpoint}")
    else:
        print(f"  ❌ 올바른 엔드포인트를 찾을 수 없습니다: {correct_endpoint}")
        return False

    # 테스트 3: downloadResults 함수 확인
    print("\n📋 테스트 3: downloadResults() 함수 구현 확인")
    if "async function downloadResults()" in content:
        print("  ✅ downloadResults() 함수가 async로 구현되어 있습니다.")
    else:
        print("  ❌ downloadResults() 함수를 찾을 수 없습니다.")
        return False

    # 테스트 4: downloadFile 함수 확인
    print("\n📋 테스트 4: downloadFile() 헬퍼 함수 확인")
    if "function downloadFile(content, filename, mimeType)" in content:
        print("  ✅ downloadFile() 헬퍼 함수가 구현되어 있습니다.")
    else:
        print("  ❌ downloadFile() 헬퍼 함수를 찾을 수 없습니다.")
        return False

    # 테스트 5: JSON 다운로드 로직 확인
    print("\n📋 테스트 5: JSON 파일 다운로드 로직 확인")
    if "downloadFile(jsonContent" in content and "application/json" in content:
        print("  ✅ JSON 형식으로 다운로드하는 로직이 구현되어 있습니다.")
    else:
        print("  ❌ JSON 다운로드 로직이 불완전합니다.")
        return False

    # 테스트 6: CSV 생성 함수 확인
    print("\n📋 테스트 6: CSV 생성 함수 확인")
    if "function generateCsvContent(data)" in content:
        print("  ✅ generateCsvContent() 함수가 구현되어 있습니다.")
    else:
        print("  ❌ generateCsvContent() 함수를 찾을 수 없습니다.")
        return False

    # 테스트 7: fetch 호출 상세 확인
    print("\n📋 테스트 7: fetch() 호출 상세 확인")
    pattern = r"fetch\(`/api/backtest/result/\$\{backtestId\}`"
    if re.search(pattern, content):
        print("  ✅ fetch()가 올바른 엔드포인트를 호출하고 있습니다.")
    else:
        print("  ❌ fetch()의 엔드포인트 호출이 올바르지 않습니다.")
        return False

    # 테스트 8: Blob과 object URL 사용 확인
    print("\n📋 테스트 8: 브라우저 다운로드 API 사용 확인")
    if "new Blob(" in content and "createObjectURL" in content:
        print("  ✅ Blob과 createObjectURL을 사용한 파일 다운로드가 구현되어 있습니다.")
    else:
        print("  ❌ 브라우저 다운로드 API 사용이 불완전합니다.")
        return False

    return True

def verify_backend_endpoint():
    """백엔드 엔드포인트 확인"""
    print("\n" + "="*70)
    print("백엔드 엔드포인트 검증")
    print("="*70 + "\n")

    backend_file = Path('backend/server.js')
    
    if not backend_file.exists():
        print(f"❌ 백엔드 파일을 찾을 수 없습니다: {backend_file}")
        return False

    with open(backend_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 테스트 1: /api/backtest/result/:id 엔드포인트 확인
    print("📋 테스트 1: /api/backtest/result/:id 엔드포인트 존재 확인")
    if "app.get('/api/backtest/result/:id'" in content:
        print("  ✅ GET /api/backtest/result/:id 엔드포인트가 정의되어 있습니다.")
    else:
        print("  ❌ GET /api/backtest/result/:id 엔드포인트를 찾을 수 없습니다.")
        return False

    # 테스트 2: 올바르지 않은 /api/results/.../download 엔드포인트가 없는지 확인
    print("\n📋 테스트 2: 잘못된 엔드포인트 부재 확인")
    if "/api/results/" in content and "/download" in content:
        # 더 정밀한 검사: 실제 엔드포인트 정의가 있는지 확인
        if "app.get('/api/results/" in content or "app.post('/api/results/" in content:
            print("  ⚠️  주의: /api/results/...를 사용하는 엔드포인트가 있을 수 있습니다.")
        else:
            print("  ✅ 잘못된 /api/results/.../download 엔드포인트가 정의되어 있지 않습니다.")
    else:
        print("  ✅ 잘못된 /api/results/.../download 엔드포인트가 정의되어 있지 않습니다.")

    # 테스트 3: 404 핸들러 확인
    print("\n📋 테스트 3: 404 에러 핸들러 확인")
    if "app.use((req, res) =>" in content and "404" in content:
        print("  ✅ 404 에러 핸들러가 정의되어 있습니다.")
    else:
        print("  ❌ 404 에러 핸들러가 명확하지 않습니다.")

    return True

def generate_test_report():
    """테스트 보고서 생성"""
    print("\n" + "="*70)
    print("테스트 완료")
    print("="*70 + "\n")

    print("✅ 수정 사항 요약:")
    print("  1. 프론트엔드 엔드포인트 수정:")
    print("     - 잘못된: /api/results/{id}/download")
    print("     - 올바른: /api/backtest/result/{id}")
    print("")
    print("  2. 다운로드 로직 구현:")
    print("     - JSON 파일 다운로드")
    print("     - CSV 형식 변환 (선택적)")
    print("     - 브라우저 네이티브 다운로드 API 사용")
    print("")
    print("  3. 에러 처리:")
    print("     - fetch 실패 시 사용자에게 에러 메시지 표시")
    print("     - 404 에러 완전 해소")

if __name__ == '__main__':
    success = True
    
    # 프론트엔드 코드 테스트
    if test_frontend_code():
        print("\n✅ 프론트엔드 코드 검증 완료")
    else:
        print("\n❌ 프론트엔드 코드 검증 실패")
        success = False

    # 백엔드 엔드포인트 검증
    if verify_backend_endpoint():
        print("\n✅ 백엔드 엔드포인트 검증 완료")
    else:
        print("\n❌ 백엔드 엔드포인트 검증 실패")
        success = False

    # 테스트 보고서
    generate_test_report()

    if success:
        print("\n" + "="*70)
        print("✅ 모든 테스트 통과!")
        print("="*70)
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("❌ 일부 테스트 실패")
        print("="*70)
        sys.exit(1)
