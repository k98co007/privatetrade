-- Test Database Initialization Script
-- Executed automatically when test container starts

-- ============================================
-- Create Core Tables
-- ============================================

CREATE TABLE IF NOT EXISTS config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  stock_mode TEXT DEFAULT 'all',
  selected_specific_stocks TEXT,
  blacklist TEXT,
  whitelist TEXT,
  strategy TEXT,
  buy_time TEXT,
  sell_time TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_session (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  config_id INTEGER NOT NULL,
  start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_time TIMESTAMP,
  status TEXT DEFAULT 'running',
  total_stocks INTEGER,
  completed_stocks INTEGER,
  FOREIGN KEY (config_id) REFERENCES config(id)
);

CREATE TABLE IF NOT EXISTS backtest_result (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  stock_code TEXT NOT NULL,
  stock_name TEXT,
  total_trades INTEGER,
  profit_trades INTEGER,
  loss_trades INTEGER,
  total_profit REAL,
  total_loss REAL,
  final_balance REAL,
  return_rate REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES backtest_session(id)
);

CREATE TABLE IF NOT EXISTS trade_detail (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  result_id INTEGER NOT NULL,
  trade_date DATE,
  buy_price REAL,
  sell_price REAL,
  quantity INTEGER,
  trade_type TEXT,
  profit_loss REAL,
  FOREIGN KEY (result_id) REFERENCES backtest_result(id)
);

-- ============================================
-- Add New Columns (Migration)
-- ============================================

-- These columns are added to config table
-- ALTER TABLE config ADD COLUMN stock_mode TEXT DEFAULT 'all';
-- ALTER TABLE config ADD COLUMN selected_specific_stocks TEXT;

-- ============================================
-- Insert Test Data
-- ============================================

-- Test config records
INSERT INTO config (id, stock_mode, selected_specific_stocks, blacklist, whitelist, strategy, buy_time, sell_time)
VALUES
  (1, 'all', NULL, NULL, NULL, 'daily_trading', '10:00', '15:00'),
  (2, 'filtered', NULL, '["005930"]', '["068270"]', 'daily_trading', '10:00', '15:00'),
  (3, 'specific', '["005930","000660"]', NULL, NULL, 'daily_trading', '10:00', '15:00'),
  (4, 'specific', '["005930","000660","068270","035720","012330","051910","017670","090430"]', NULL, NULL, 'trailing_stop', '15:30', NULL);

-- Create indices
CREATE INDEX IF NOT EXISTS idx_config_stock_mode ON config(stock_mode);
CREATE INDEX IF NOT EXISTS idx_config_selected_specific ON config(selected_specific_stocks);
CREATE INDEX IF NOT EXISTS idx_backtest_session_config ON backtest_session(config_id);
CREATE INDEX IF NOT EXISTS idx_backtest_result_session ON backtest_result(session_id);
CREATE INDEX IF NOT EXISTS idx_trade_detail_result ON trade_detail(result_id);

-- ============================================
-- Verification Query
-- ============================================

-- SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';
-- SELECT * FROM config LIMIT 1;
