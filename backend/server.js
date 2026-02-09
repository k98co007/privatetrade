/**
 * Backend Server - PrivateTrade Backtesting Simulator
 * Version: 2.0.0
 * Main entry point for Express.js server
 */

const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Static files (Frontend)
app.use(express.static(path.join(__dirname, '..', 'frontend')));

// Routes imports
const stocksRouter = require('./routes/stocks');
const { PythonWorker } = require('./utils/pythonWorker');
const { getCache } = require('./utils/dataCache');

// Backtesting Progress Tracking
const backtestProgress = {}; // { backtestId: { percent, status, startTime, trades } }

// Backtesting Results Store
const backtestResults = {}; // { backtestId: { status, data, error, completedAt } }

// Initialize Data Cache (SRS NFR-301: 일일 1회 수집)
const dataCache = getCache();
dataCache.cleanupOldCache(3); // 3일 이전 캐시 정리
console.log('[Backend] Data cache initialized:', dataCache.getStats());

// Initialize Python Worker
let pythonWorker = null;
const initPythonWorker = async () => {
  if (!pythonWorker) {
    pythonWorker = new PythonWorker('python'); // Windows에서 'python' 사용
    try {
      await pythonWorker.start();
      console.log('[Backend] Python Worker connected');
    } catch (error) {
      console.error('[Backend] Failed to start Python Worker:', error);
      pythonWorker = null;
    }
  }
  return pythonWorker;
};

// ============================================
// API Routes
// ============================================

// Health check endpoint
app.get('/api/health', (req, res) => {
  const uptime = Math.floor(process.uptime());
  res.json({
    status: 'healthy',
    version: '2.0.0',
    uptime: uptime,
    services: {
      database: 'connected',
      python_worker: 'ready'
    }
  });
});

// Stock management routes
app.use('/api/stocks', stocksRouter);

// Cache stats endpoint (SRS NFR-301)
app.get('/api/cache/stats', (req, res) => {
  res.json({
    success: true,
    ...dataCache.getStats()
  });
});

// Cache invalidation endpoint
app.delete('/api/cache/:code', (req, res) => {
  const { code } = req.params;
  if (code === 'all') {
    dataCache.invalidateAll();
  } else {
    dataCache.invalidate(code);
  }
  res.json({
    success: true,
    message: code === 'all' ? 'All cache cleared' : `Cache cleared for ${code}`,
    ...dataCache.getStats()
  });
});

// ============================================
// Basic Backtest API (Placeholder)
// ============================================

app.post('/api/backtest/start', async (req, res) => {
  const {
    strategy,
    start_date,
    end_date,
    initial_capital,
    stock_mode
  } = req.body;

  try {
    if (!strategy) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: strategy'
      });
    }

    // 날짜 미지정 시 최근 60일로 기본 설정
    const now = new Date();
    const sixtyDaysAgo = new Date(now);
    sixtyDaysAgo.setDate(now.getDate() - 60);
    const effectiveEndDate = end_date || now.toISOString().split('T')[0];
    const effectiveStartDate = start_date || sixtyDaysAgo.toISOString().split('T')[0];

    const backtestId = `bt-${new Date().toISOString().split('T')[0]}-${Math.floor(Math.random() * 1000)}`;

    console.log(`[API] POST /api/backtest/start - Backtest ${backtestId} started`);
    console.log(`  Strategy: ${strategy}, Mode: ${stock_mode}, Capital: ${initial_capital}`);

    // Initialize Python Worker if not already done
    const worker = await initPythonWorker();

    if (worker) {
      // Build strategy object from request
      // 전략 1 (daily_trading) / 전략 2 (trailing_stop) 지원 (LLD 3.3.2, 3.3.3)
      const strategyParams = req.body.strategy_params || {};
      let strategyObj;

      if (strategy === 'daily_trading' || strategyParams.type === 'daily_trading') {
        // 전략 1: 고정시간 매수/매도
        strategyObj = {
          type: 'daily_trading',
          buy_time: strategyParams.buy_time || '10:00',
          sell_time: strategyParams.sell_time || '15:00'
        };
      } else if (strategy === 'trailing_stop' || strategyParams.type === 'trailing_stop') {
        // 전략 2: Trailing Stop
        strategyObj = {
          type: 'trailing_stop',
          buy_time: strategyParams.buy_time || '15:30',
          min_profit_pct: strategyParams.min_profit_pct || 1.0,
          profit_cutoff_pct: strategyParams.profit_cutoff_pct || 80.0,
          loss_cutoff_time: strategyParams.loss_cutoff_time || '14:00'
        };
      } else {
        // 레거시 전략 호환
        const legacyConfig = {
          'MA20_50': { buy_time: '09:30', sell_time: '15:50', signal_type: 'moving_average', ma_short: 20, ma_long: 50 },
          'MA5_20': { buy_time: '09:30', sell_time: '15:50', signal_type: 'moving_average', ma_short: 5, ma_long: 20 },
          'RSI': { buy_time: '09:30', sell_time: '15:50', signal_type: 'simple_time', rsi_threshold: 30 },
          'MACD': { buy_time: '09:30', sell_time: '15:50', signal_type: 'simple_time' }
        };
        strategyObj = legacyConfig[strategy] || { buy_time: '09:30', sell_time: '15:50' };
      }

      // Send backtest request to Python Worker
      // 가격 데이터는 Python 엔진이 직접 Yahoo Finance에서 조회
      const pythonRequest = {
        stock_code: req.body.stock_code || '005930',
        strategy: strategyObj,
        initial_capital: initial_capital || 10000000,
        backtest_id: backtestId,
        start_date: effectiveStartDate,
        end_date: effectiveEndDate,
        stock_mode: stock_mode
      };

      console.log(`[API] Sending request to Python Worker for ${backtestId}`);
      console.log(`  Strategy config:`, JSON.stringify(strategyObj));
      console.log(`  Date range: ${effectiveStartDate} ~ ${effectiveEndDate}`);
      
      // Initialize result entry as running
      backtestResults[backtestId] = { status: 'running', data: null, error: null, completedAt: null };

      worker.execute(pythonRequest)
        .then((result) => {
          console.log(`[API] Python Worker returned result for ${backtestId}`);
          console.log(`  Result:`, JSON.stringify(result).substring(0, 200) + '...');
          
          // Store actual backtest results
          backtestResults[backtestId] = {
            status: 'completed',
            data: result,
            error: null,
            completedAt: new Date().toISOString()
          };

          // Mark progress as completed
          if (backtestProgress[backtestId]) {
            backtestProgress[backtestId].status = 'completed';
            backtestProgress[backtestId].percent = 100;
          }
        })
        .catch((error) => {
          console.error(`[API] Python Worker error for ${backtestId}:`, error.message);
          
          // Store error status
          backtestResults[backtestId] = {
            status: 'error',
            data: null,
            error: error.message,
            completedAt: new Date().toISOString()
          };

          if (backtestProgress[backtestId]) {
            backtestProgress[backtestId].status = 'error';
          }
        });
    } else {
      console.warn('[API] Python Worker not available - running in mock mode');
    }

    res.json({
      success: true,
      backtest_id: backtestId,
      status: 'running',
      message: `Backtest started with strategy: ${strategy}`,
      worker_status: worker ? 'connected' : 'offline'
    });
  } catch (error) {
    console.error('[API] Error starting backtest:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/backtest/progress', (req, res) => {
  const { id } = req.query;

  if (!id) {
    return res.status(400).json({
      success: false,
      error: 'backtest_id parameter is required'
    });
  }

  // Initialize backtest progress if not exists
  if (!backtestProgress[id]) {
    backtestProgress[id] = {
      percent: 0,
      status: 'running',
      startTime: Date.now(),
      trades: 0
    };
  }

  const progress = backtestProgress[id];
  const elapsed = (Date.now() - progress.startTime) / 1000; // Time in seconds

  // Progress increases 10% every 1 second (max 100%)
  progress.percent = Math.min(Math.floor(elapsed / 1) * 10, 100);
  
  // Update trades based on progress
  progress.trades = Math.floor(progress.percent / 10) * 25;

  // When progress reaches 100%, mark as completed
  if (progress.percent >= 100) {
    progress.status = 'completed';
  }

  res.json({
    backtest_id: id,
    status: progress.status,
    progress_percent: progress.percent,
    current_date: '2024-06-15',
    total_trades: progress.trades
  });
});

app.get('/api/backtest/result/:id', (req, res) => {
  const { id } = req.params;

  const stored = backtestResults[id];

  // No result found for this ID
  if (!stored) {
    return res.status(404).json({
      backtest_id: id,
      status: 'not_found',
      error: 'No backtest found with this ID'
    });
  }

  // Backtest still running
  if (stored.status === 'running') {
    return res.json({
      backtest_id: id,
      status: 'running',
      message: 'Backtest is still in progress'
    });
  }

  // Backtest failed
  if (stored.status === 'error') {
    return res.json({
      backtest_id: id,
      status: 'error',
      error: stored.error,
      completed_at: stored.completedAt
    });
  }

  // Backtest completed - return actual results
  const data = stored.data || {};
  const metrics = data.metrics || {};

  res.json({
    backtest_id: id,
    status: 'completed',
    stock_code: data.stock_code || null,
    strategy: data.strategy || null,
    initial_capital: data.initial_capital || 0,
    final_capital: data.final_capital || 0,
    performance: {
      total_return: metrics.total_return != null ? `${metrics.total_return.toFixed(2)}%` : `${(data.return_rate || 0).toFixed(2)}%`,
      annual_return: metrics.annual_return != null ? `${metrics.annual_return.toFixed(2)}%` : null,
      sharpe_ratio: metrics.sharpe_ratio != null ? parseFloat(metrics.sharpe_ratio.toFixed(2)) : 0,
      sortino_ratio: metrics.sortino_ratio != null ? parseFloat(metrics.sortino_ratio.toFixed(2)) : null,
      calmar_ratio: metrics.calmar_ratio != null ? parseFloat(metrics.calmar_ratio.toFixed(2)) : null,
      max_drawdown: `${-(data.mdd || metrics.mdd || 0).toFixed(2)}%`,
      volatility: metrics.annual_volatility != null ? `${metrics.annual_volatility.toFixed(2)}%` : null,
      total_trades: data.total_trades || 0,
      winning_trades: data.winning_trades || 0,
      losing_trades: data.losing_trades || 0,
      win_rate: `${(data.win_rate || metrics.win_rate || 0).toFixed(1)}%`,
      profit_factor: parseFloat((data.profit_factor || metrics.profit_factor || 0).toFixed(2)),
      avg_win: data.avg_win || metrics.avg_win || 0,
      avg_loss: data.avg_loss || metrics.avg_loss || 0,
      expectancy: metrics.expectancy || null,
      total_profit: data.total_profit || 0,
      total_cost: data.total_cost || 0
    },
    sell_reason_stats: data.sell_reason_stats || null,
    equity_curve: data.equity_curve || [],
    trading_log: data.trading_log || [],
    completed_at: stored.completedAt
  });
});

// ============================================
// CSV Download Endpoint
// ============================================

app.get('/api/backtest/result/:id/csv', (req, res) => {
  const { id } = req.params;

  const stored = backtestResults[id];

  if (!stored) {
    return res.status(404).json({ error: 'No backtest found with this ID' });
  }

  if (stored.status !== 'completed') {
    return res.status(400).json({ error: `Backtest status is '${stored.status}', not completed` });
  }

  const data = stored.data || {};
  const tradingLog = data.trading_log || [];
  const strategyType = data.strategy || '';

  if (!tradingLog.length) {
    return res.status(404).json({ error: 'No trading log data available' });
  }

  // Determine if strategy 2 (has sell_reason field)
  const isStrategy2 = (
    strategyType === 'strategy2_trailing_stop' ||
    tradingLog.some(t => t.sell_reason !== undefined)
  );

  // Build CSV content with UTF-8 BOM for Excel Korean support
  const BOM = '\uFEFF';
  const lines = [];

  // Summary header
  lines.push('백테스트 매매 내역');
  lines.push(`백테스트 ID,${id}`);
  lines.push(`종목코드,${data.stock_code || '-'}`);
  lines.push(`전략,${strategyType}`);
  lines.push(`초기자본,${(data.initial_capital || 0).toLocaleString()}`);
  lines.push(`최종자본,${(data.final_capital || 0).toLocaleString()}`);
  lines.push(`총수익률,${(data.return_rate || 0).toFixed(2)}%`);
  lines.push(`총거래수,${data.total_trades || 0}`);
  lines.push(`승률,${(data.win_rate || 0).toFixed(1)}%`);
  lines.push(`MDD,${(data.mdd || 0).toFixed(2)}%`);
  lines.push(`총비용(세금+수수료),${Math.round(data.total_cost || 0).toLocaleString()}`);
  lines.push('');

  // Trading log header
  if (isStrategy2) {
    lines.push('번호,매수일시,매수가,매도일시,매도가,투입금액,매매차익,비용(세금+수수료),순수익,거래후잔고,매도사유,최고가,최대수익률(%)');
  } else {
    lines.push('번호,매수일시,매수가,매도일시,매도가,투입금액,매매차익,비용(세금+수수료),순수익,거래후잔고');
  }

  // Sell reason Korean mapping
  const sellReasonMap = {
    'trailing_stop': '트레일링스탑',
    'loss_cutoff': '손절',
    'end_of_day': '장마감매도'
  };

  // Trading log rows
  tradingLog.forEach((trade, idx) => {
    // Escape CSV fields that might contain commas
    const escapeCSV = (val) => {
      const str = String(val);
      return str.includes(',') ? `"${str}"` : str;
    };

    const row = [
      idx + 1,
      escapeCSV(trade.buy_time || ''),
      trade.buy_price || '',
      escapeCSV(trade.sell_time || ''),
      trade.sell_price || '',
      Math.round(trade.buy_amount || 0),
      Math.round(trade.gross_profit || 0),
      Math.round(trade.cost || 0),
      Math.round(trade.profit || 0),
      Math.round(trade.balance_after || 0)
    ];

    if (isStrategy2) {
      const reason = trade.sell_reason || '';
      row.push(
        sellReasonMap[reason] || reason,
        trade.highest_price || '',
        (trade.max_profit_pct || 0).toFixed(2)
      );
    }

    lines.push(row.join(','));
  });

  const csvContent = BOM + lines.join('\n');
  
  const stockCode = data.stock_code || 'unknown';
  const filename = `backtest-trades-${stockCode}-${id}.csv`;

  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
  res.send(csvContent);

  console.log(`[API] CSV downloaded for ${id}: ${tradingLog.length} trades`);
});

// ============================================
// Frontend Routes
// ============================================

// Serve specific-stock-selection page
app.get('/pages/specific-stock-selection.html', (req, res) => {
  const filePath = path.join(__dirname, '..', 'frontend', 'pages', 'specific-stock-selection.html');
  res.sendFile(filePath);
});

// Root route - serve index
app.get('/', (req, res) => {
  const indexPath = path.join(__dirname, '..', 'frontend', 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.json({
      message: 'PrivateTrade Backtesting Simulator v2.0.0',
      api_base: '/api',
      endpoints: {
        health: 'GET /api/health',
        stocks: {
          mode: 'POST /api/stocks/mode',
          specific_add: 'POST /api/stocks/specific/add',
          specific_get: 'GET /api/stocks/specific',
          specific_delete: 'DELETE /api/stocks/specific/:code'
        },
        backtest: {
          start: 'POST /api/backtest/start',
          progress: 'GET /api/backtest/progress',
          result: 'GET /api/backtest/result/:id'
        }
      }
    });
  }
});

// ============================================
// Error Handling
// ============================================

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `${req.method} ${req.path} not found`,
    available_endpoints: [
      'GET /api/health',
      'POST /api/stocks/mode',
      'POST /api/stocks/specific/add',
      'GET /api/stocks/specific',
      'DELETE /api/stocks/specific/:code',
      'POST /api/backtest/start',
      'GET /api/backtest/progress',
      'GET /api/backtest/result/:id'
    ]
  });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('[ERROR]', err);
  res.status(500).json({
    success: false,
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal Server Error' 
      : err.message,
    stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
  });
});

// ============================================
// Server Startup
// ============================================

const server = app.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════╗
║                                           ║
║   PrivateTrade Backtesting Simulator      ║
║   Version: 2.0.0                          ║
║                                           ║
║   ✓ Server running on port ${PORT}        ║
║   ✓ Frontend: http://localhost:${PORT}    ║
║   ✓ API Base: http://localhost:${PORT}/api ║
║                                           ║
╚═══════════════════════════════════════════╝
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    console.log('HTTP server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received: closing HTTP server');
  server.close(() => {
    console.log('HTTP server closed');
    process.exit(0);
  });
});

module.exports = app;
