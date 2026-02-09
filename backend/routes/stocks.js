/**
 * API Routes for Stock Management
 * Endpoints for:
 * - stock_mode switching (all/filtered/specific)
 * - specific stock addition/removal
 * - specific stock retrieval
 */

const express = require('express');
const router = express.Router();

// Mock ConfigRepository (실제는 DB 연동)
const mockConfigDb = {
  stock_mode: 'all',
  selected_specific_stocks: []
};

/**
 * POST /api/stocks/mode
 * 종목 선택 모드 전환
 */
router.post('/mode', (req, res) => {
  try {
    const { mode } = req.body;

    console.log(`[API] POST /api/stocks/mode - Request: ${mode}`);

    // 유효성 검사
    if (!mode) {
      return res.status(400).json({
        success: false,
        error: 'mode field is required'
      });
    }

    if (!['all', 'filtered', 'specific'].includes(mode)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid stock_mode. Must be: all, filtered, or specific'
      });
    }

    // 모드 업데이트
    mockConfigDb.stock_mode = mode;
    
    // 특정 종목 모드가 아니면 특정 종목 초기화
    if (mode !== 'specific') {
      mockConfigDb.selected_specific_stocks = [];
    }

    console.log(`[API] Mode changed to: ${mode}`);

    res.json({
      success: true,
      current_mode: mode,
      message: `Stock mode changed to '${mode}'`
    });
  } catch (error) {
    console.error('[API] /api/stocks/mode error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * POST /api/stocks/specific/add
 * 특정 종목 추가
 */
router.post('/specific/add', (req, res) => {
  try {
    const { codes } = req.body;

    console.log(`[API] POST /api/stocks/specific/add - Request codes: ${JSON.stringify(codes)}`);

    // 유효성 검사
    if (!Array.isArray(codes) || codes.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'codes must be a non-empty array'
      });
    }

    if (codes.length > 100) {
      return res.status(400).json({
        success: false,
        error: 'Maximum 100 stocks allowed'
      });
    }

    // 종목 코드 형식 검증 (6자리 숫자)
    const codeRegex = /^\d{6}$/;
    const invalidCodes = codes.filter(code => !codeRegex.test(code));
    
    if (invalidCodes.length > 0) {
      return res.status(400).json({
        success: false,
        error: `Invalid stock codes: ${invalidCodes.join(', ')}`
      });
    }

    // 중복 제거
    const uniqueCodes = [...new Set(codes)];

    // 저장
    mockConfigDb.stock_mode = 'specific';
    mockConfigDb.selected_specific_stocks = uniqueCodes;

    console.log(`[API] Added ${uniqueCodes.length} specific stocks`);

    res.json({
      success: true,
      selected_count: uniqueCodes.length,
      selected_stocks: uniqueCodes,
      message: `Successfully added ${uniqueCodes.length} stocks`
    });
  } catch (error) {
    console.error('[API] /api/stocks/specific/add error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/stocks/specific
 * 특정 종목 조회
 */
router.get('/specific', (req, res) => {
  try {
    console.log('[API] GET /api/stocks/specific');

    res.json({
      current_mode: mockConfigDb.stock_mode,
      selected_count: mockConfigDb.selected_specific_stocks.length,
      selected_stocks: mockConfigDb.selected_specific_stocks
    });
  } catch (error) {
    console.error('[API] /api/stocks/specific error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * DELETE /api/stocks/specific/:code
 * 특정 종목 제거
 */
router.delete('/specific/:code', (req, res) => {
  try {
    const { code } = req.params;

    console.log(`[API] DELETE /api/stocks/specific/${code}`);

    // 유효성 검사
    const codeRegex = /^\d{6}$/;
    if (!codeRegex.test(code)) {
      return res.status(400).json({
        success: false,
        error: `Invalid stock code format: ${code}`
      });
    }

    // 종목 제거
    mockConfigDb.selected_specific_stocks = 
      mockConfigDb.selected_specific_stocks.filter(c => c !== code);

    console.log(`[API] Removed stock: ${code}`);

    res.json({
      success: true,
      selected_count: mockConfigDb.selected_specific_stocks.length,
      message: `Stock ${code} removed successfully`
    });
  } catch (error) {
    console.error('[API] /api/stocks/specific/:code error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * DELETE /api/stocks/specific/clear
 * 특정 종목 전체 초기화 (선택 사항)
 */
router.delete('/specific', (req, res) => {
  try {
    console.log('[API] DELETE /api/stocks/specific (clear all)');

    mockConfigDb.selected_specific_stocks = [];

    res.json({
      success: true,
      message: 'All specific stocks cleared'
    });
  } catch (error) {
    console.error('[API] Clear specific stocks error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
