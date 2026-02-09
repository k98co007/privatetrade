-- Migration: Add specific stock selection feature
-- Created: 2026-02-08
-- Version: 2.0

-- ============================================
-- Add new columns to config table
-- ============================================

ALTER TABLE config ADD COLUMN stock_mode TEXT DEFAULT 'all';
-- Enum values: 'all' | 'filtered' | 'specific'
-- Default: 'all' (backward compatibility)

ALTER TABLE config ADD COLUMN selected_specific_stocks TEXT;
-- JSON array: '["005930", "000660", ...]'
-- NULL or '[]' if not in specific mode

-- ============================================
-- Ensure backward compatibility
-- ============================================

-- Update existing configs to 'all' mode if NULL
UPDATE config SET stock_mode = 'all' WHERE stock_mode IS NULL;

-- ============================================
-- Create index for better query performance
-- ============================================

CREATE INDEX idx_config_stock_mode ON config(stock_mode);
CREATE INDEX idx_config_selected_specific ON config(selected_specific_stocks);

-- ============================================
-- Verify migration
-- ============================================

-- Check new columns exist
-- SELECT * FROM config LIMIT 1;
