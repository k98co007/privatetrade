/**
 * StockFilter Module
 * 역할: 종목 모드에 따라 백테스팅 대상 종목 필터링
 * 
 * 지원 모드:
 * - 'all': 코스피 200 전체
 * - 'filtered': 블랙/화이트리스트 적용
 * - 'specific': 사용자가 직접 선택한 종목
 */

class StockFilter {
  constructor(kospi200Codes = []) {
    this.kospi200Codes = kospi200Codes || [];
  }

  /**
   * 종목 리스트 필터링
   * @param {string} mode - 'all' | 'filtered' | 'specific'
   * @param {array} blacklist - 블랙리스트 종목 코드
   * @param {array} whitelist - 화이트리스트 종목 코드
   * @param {array} specificStocks - 특정 종목 코드 (mode='specific'일 때)
   * @returns {array} 필터링된 종목 코드 배열
   * @throws {Error} 유효하지 않은 모드
   */
  applyFilter(mode, blacklist = [], whitelist = [], specificStocks = []) {
    console.log(`[StockFilter] Applying filter. Mode: ${mode}, Blacklist: ${blacklist.length}, Whitelist: ${whitelist.length}, Specific: ${specificStocks.length}`);

    switch (mode) {
      case 'all':
        return this.kospi200Codes;
      
      case 'filtered':
        return this.applyBlackWhiteFilter(blacklist, whitelist);
      
      case 'specific':
        return this.applySpecificFilter(specificStocks);
      
      default:
        throw new Error(`Unknown stock_mode: ${mode}`);
    }
  }

  /**
   * 블랙/화이트리스트 필터링
   * @private
   */
  applyBlackWhiteFilter(blacklist, whitelist) {
    // KOSPI 200에서 블랙리스트 제거
    let result = this.kospi200Codes.filter(code => !blacklist.includes(code));
    
    // 화이트리스트 추가
    if (whitelist && whitelist.length > 0) {
      result = [...new Set([...result, ...whitelist])];
    }
    
    console.log(`[StockFilter] Filtered result (mode=filtered): ${result.length} stocks`);
    return result;
  }

  /**
   * 특정 종목만 필터링
   * @private
   */
  applySpecificFilter(specificStocks) {
    // 1. 종목 코드 유효성 검증
    const invalidCodes = specificStocks.filter(code => !this.isValidStockCode(code));
    if (invalidCodes.length > 0) {
      throw new Error(`Invalid stock codes: ${invalidCodes.join(', ')}`);
    }

    // 2. KOSPI 200 또는 화이트리스트에 속하는 종목만 선택
    const validStocks = specificStocks.filter(code =>
      this.kospi200Codes.includes(code) // 일단 KOSPI 200만 체크
    );

    console.log(`[StockFilter] Filtered result (mode=specific): ${validStocks.length}/${specificStocks.length} valid stocks`);
    return validStocks;
  }

  /**
   * 종목 코드 형식 검증 (6자리 숫자)
   * @private
   */
  isValidStockCode(code) {
    return /^\d{6}$/.test(code);
  }
}

module.exports = StockFilter;
