-- ============================================================================
-- Database Optimization Migration
-- Senior PostgreSQL Database Architect
-- 
-- Fixes:
-- 1. Missing Foreign Keys
-- 2. Missing Indexes
-- 3. Monetary Decimal Types (Float → Numeric(12,2))
-- 4. Vendor Wallet Optimization
-- 5. Vendor Transaction Optimization
-- 6. Vendor Settlement Optimization
-- ============================================================================

BEGIN;

-- ============================================================================
-- PART 1: ADD MISSING FOREIGN KEYS
-- ============================================================================

-- 1.1 vendor_wallets → users (already exists, ensure CASCADE)
ALTER TABLE vendor_wallets
    DROP CONSTRAINT IF EXISTS vendor_wallets_vendor_id_fkey,
    ADD CONSTRAINT vendor_wallets_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- 1.2 vendor_transactions → users
ALTER TABLE vendor_transactions
    DROP CONSTRAINT IF EXISTS vendor_transactions_vendor_id_fkey,
    ADD CONSTRAINT vendor_transactions_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- 1.3 vendor_transactions → orders
ALTER TABLE vendor_transactions
    DROP CONSTRAINT IF EXISTS vendor_transactions_order_id_fkey,
    ADD CONSTRAINT vendor_transactions_order_id_fkey
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE SET NULL;

-- 1.4 vendor_transactions → payments
ALTER TABLE vendor_transactions
    DROP CONSTRAINT IF EXISTS vendor_transactions_payment_id_fkey,
    ADD CONSTRAINT vendor_transactions_payment_id_fkey
        FOREIGN KEY (payment_id) REFERENCES payments(id)
        ON DELETE SET NULL;

-- 1.5 vendor_settlements → users
ALTER TABLE vendor_settlements
    DROP CONSTRAINT IF EXISTS vendor_settlements_vendor_id_fkey,
    ADD CONSTRAINT vendor_settlements_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- 1.6 vendor_refunds → users
ALTER TABLE vendor_refunds
    DROP CONSTRAINT IF EXISTS vendor_refunds_vendor_id_fkey,
    ADD CONSTRAINT vendor_refunds_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- 1.7 vendor_refunds → orders
ALTER TABLE vendor_refunds
    DROP CONSTRAINT IF EXISTS vendor_refunds_order_id_fkey,
    ADD CONSTRAINT vendor_refunds_order_id_fkey
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE;

-- 1.8 vendor_refunds → payments
ALTER TABLE vendor_refunds
    DROP CONSTRAINT IF EXISTS vendor_refunds_payment_id_fkey,
    ADD CONSTRAINT vendor_refunds_payment_id_fkey
        FOREIGN KEY (payment_id) REFERENCES payments(id)
        ON DELETE SET NULL;

-- 1.9 vendor_profiles → users
ALTER TABLE vendor_profiles
    DROP CONSTRAINT IF EXISTS vendor_profiles_vendor_id_fkey,
    ADD CONSTRAINT vendor_profiles_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- 1.10 vendor_retention → users
ALTER TABLE vendor_retention_rules
    DROP CONSTRAINT IF EXISTS vendor_retention_rules_vendor_id_fkey,
    ADD CONSTRAINT vendor_retention_rules_vendor_id_fkey
        FOREIGN KEY (vendor_id) REFERENCES users(id)
        ON DELETE CASCADE;

-- ============================================================================
-- PART 2: CONVERT FLOAT TO NUMERIC(12,2) FOR MONETARY COLUMNS
-- ============================================================================

-- 2.1 vendor_wallets - Convert all monetary columns to NUMERIC(12,2)
ALTER TABLE vendor_wallets
    ALTER COLUMN total_earned TYPE NUMERIC(12,2) USING total_earned::NUMERIC(12,2),
    ALTER COLUMN total_pending TYPE NUMERIC(12,2) USING total_pending::NUMERIC(12,2),
    ALTER COLUMN total_settled TYPE NUMERIC(12,2) USING total_settled::NUMERIC(12,2),
    ALTER COLUMN total_refunded TYPE NUMERIC(12,2) USING total_refunded::NUMERIC(12,2),
    ALTER COLUMN balance TYPE NUMERIC(12,2) USING balance::NUMERIC(12,2);

-- 2.2 vendor_transactions - Convert all monetary columns to NUMERIC(12,2)
ALTER TABLE vendor_transactions
    ALTER COLUMN amount TYPE NUMERIC(12,2) USING amount::NUMERIC(12,2),
    ALTER COLUMN fee TYPE NUMERIC(12,2) USING fee::NUMERIC(12,2),
    ALTER COLUMN net_amount TYPE NUMERIC(12,2) USING net_amount::NUMERIC(12,2);

-- 2.3 vendor_settlements - Convert all monetary columns to NUMERIC(12,2)
ALTER TABLE vendor_settlements
    ALTER COLUMN total_amount TYPE NUMERIC(12,2) USING total_amount::NUMERIC(12,2),
    ALTER COLUMN total_fees TYPE NUMERIC(12,2) USING total_fees::NUMERIC(12,2),
    ALTER COLUMN net_amount TYPE NUMERIC(12,2) USING net_amount::NUMERIC(12,2),
    ALTER COLUMN online_payments TYPE NUMERIC(12,2) USING online_payments::NUMERIC(12,2),
    ALTER COLUMN cash_orders TYPE NUMERIC(12,2) USING cash_orders::NUMERIC(12,2),
    ALTER COLUMN refunds TYPE NUMERIC(12,2) USING refunds::NUMERIC(12,2);

-- 2.4 vendor_refunds - Convert amount to NUMERIC(12,2)
ALTER TABLE vendor_refunds
    ALTER COLUMN amount TYPE NUMERIC(12,2) USING amount::NUMERIC(12,2);

-- 2.5 orders - Convert monetary columns if they exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'total_amount') THEN
        ALTER TABLE orders ALTER COLUMN total_amount TYPE NUMERIC(12,2) USING total_amount::NUMERIC(12,2);
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'delivery_fee') THEN
        ALTER TABLE orders ALTER COLUMN delivery_fee TYPE NUMERIC(12,2) USING delivery_fee::NUMERIC(12,2);
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'platform_fee') THEN
        ALTER TABLE orders ALTER COLUMN platform_fee TYPE NUMERIC(12,2) USING platform_fee::NUMERIC(12,2);
    END IF;
END $$;

-- 2.6 menu_items - Convert price to NUMERIC(12,2)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'menu_items' AND column_name = 'price') THEN
        ALTER TABLE menu_items ALTER COLUMN price TYPE NUMERIC(12,2) USING price::NUMERIC(12,2);
    END IF;
END $$;

-- ============================================================================
-- PART 3: ADD MISSING INDEXES
-- ============================================================================

-- 3.1 Vendor Wallet Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_wallets_vendor_id ON vendor_wallets(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_wallets_balance ON vendor_wallets(balance);
CREATE INDEX IF NOT EXISTS idx_vendor_wallets_updated ON vendor_wallets(updated_at);

-- 3.2 Vendor Transaction Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_vendor_id ON vendor_transactions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_order_id ON vendor_transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_payment_id ON vendor_transactions(payment_id);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_type ON vendor_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_status ON vendor_transactions(status);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_created ON vendor_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_vendor_created ON vendor_transactions(vendor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vendor_transactions_vendor_type ON vendor_transactions(vendor_id, transaction_type);

-- 3.3 Vendor Settlement Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_vendor_id ON vendor_settlements(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_status ON vendor_settlements(status);
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_period ON vendor_settlements(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_vendor_status ON vendor_settlements(vendor_id, status);
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_vendor_period ON vendor_settlements(vendor_id, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_vendor_settlements_created ON vendor_settlements(created_at DESC);

-- 3.4 Vendor Refund Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_vendor_id ON vendor_refunds(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_order_id ON vendor_refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_payment_id ON vendor_refunds(payment_id);
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_status ON vendor_refunds(status);
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_vendor_status ON vendor_refunds(vendor_id, status);
CREATE INDEX IF NOT EXISTS idx_vendor_refunds_created ON vendor_refunds(created_at DESC);

-- 3.5 Vendor Profile Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_vendor_id ON vendor_profiles(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_business_name ON vendor_profiles(business_name);

-- 3.6 Retention Rule Indexes
CREATE INDEX IF NOT EXISTS idx_retention_rules_vendor_id ON vendor_retention_rules(vendor_id);
CREATE INDEX IF NOT EXISTS idx_retention_rules_active ON vendor_retention_rules(is_active);

-- 3.7 Orders Indexes for JOIN performance
CREATE INDEX IF NOT EXISTS idx_orders_vendor_id ON orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_vendor_status ON orders(vendor_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_vendor_created ON orders(vendor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at DESC);

-- 3.8 Order Items Indexes
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_menu_item_id ON order_items(menu_item_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_menu ON order_items(order_id, menu_item_id);

-- 3.9 Menu Items Indexes
CREATE INDEX IF NOT EXISTS idx_menu_items_vendor_id ON menu_items(vendor_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_available ON menu_items(is_available);

-- 3.10 Payment Indexes
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_vendor_id ON payments(vendor_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ============================================================================
-- PART 4: ADD CONSTRAINTS AND DEFAULTS
-- ============================================================================

-- 4.1 Add NOT NULL constraints where appropriate
ALTER TABLE vendor_transactions
    ALTER COLUMN amount SET NOT NULL,
    ALTER COLUMN net_amount SET NOT NULL,
    ALTER COLUMN transaction_type SET NOT NULL;

ALTER TABLE vendor_settlements
    ALTER COLUMN total_amount SET NOT NULL,
    ALTER COLUMN net_amount SET NOT NULL,
    ALTER COLUMN period_start SET NOT NULL,
    ALTER COLUMN period_end SET NOT NULL;

-- 4.2 Add CHECK constraints for data integrity
ALTER TABLE vendor_wallets
    ADD CONSTRAINT chk_wallet_balance_non_negative 
        CHECK (balance >= 0),
    ADD CONSTRAINT chk_wallet_earned_non_negative 
        CHECK (total_earned >= 0),
    ADD CONSTRAINT chk_wallet_pending_non_negative 
        CHECK (total_pending >= 0);

ALTER TABLE vendor_transactions
    ADD CONSTRAINT chk_transaction_amount_positive 
        CHECK (amount > 0),
    ADD CONSTRAINT chk_transaction_fee_non_negative 
        CHECK (fee >= 0);

ALTER TABLE vendor_settlements
    ADD CONSTRAINT chk_settlement_dates_valid 
        CHECK (period_end > period_start),
    ADD CONSTRAINT chk_settlement_amount_positive 
        CHECK (total_amount > 0);

ALTER TABLE vendor_refunds
    ADD CONSTRAINT chk_refund_amount_positive 
        CHECK (amount > 0);

-- ============================================================================
-- PART 5: ADD AUDIT COLUMNS
-- ============================================================================

-- 5.1 Add audit columns to vendor_wallets
ALTER TABLE vendor_wallets
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP;

-- 5.2 Add audit columns to vendor_transactions
ALTER TABLE vendor_transactions
    ADD COLUMN IF NOT EXISTS reference VARCHAR(100),
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS reconciled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP;

-- 5.3 Add audit columns to vendor_settlements
ALTER TABLE vendor_settlements
    ADD COLUMN IF NOT EXISTS transaction_ids INTEGER[],
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS reconciled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP;

-- ============================================================================
-- PART 6: CREATE MATERIALIZED VIEWS FOR COMMON QUERIES
-- ============================================================================

-- 6.1 Vendor Financial Summary (cached for dashboard)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vendor_financial_summary AS
SELECT
    vw.vendor_id,
    vw.balance AS current_balance,
    vw.total_earned,
    vw.total_pending,
    vw.total_settled,
    vw.total_refunded,
    COALESCE(SUM(vt.amount) FILTER (WHERE vt.created_at >= NOW() - INTERVAL '7 days'), 0) AS weekly_revenue,
    COALESCE(SUM(vt.amount) FILTER (WHERE vt.created_at >= NOW() - INTERVAL '30 days'), 0) AS monthly_revenue,
    COALESCE(COUNT(vt.id) FILTER (WHERE vt.created_at >= NOW() - INTERVAL '30 days'), 0) AS monthly_transactions,
    COALESCE(SUM(vs.net_amount) FILTER (WHERE vs.status = 'completed' AND vs.settled_at >= NOW() - INTERVAL '30 days'), 0) AS monthly_settled
FROM vendor_wallets vw
LEFT JOIN vendor_transactions vt ON vt.vendor_id = vw.vendor_id
LEFT JOIN vendor_settlements vs ON vs.vendor_id = vw.vendor_id
GROUP BY vw.vendor_id, vw.balance, vw.total_earned, vw.total_pending, vw.total_settled, vw.total_refunded;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_financial_summary_vendor ON mv_vendor_financial_summary(vendor_id);

-- 6.2 Vendor Transaction History (cached for listings)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vendor_transaction_history AS
SELECT
    vt.id,
    vt.vendor_id,
    vt.transaction_type,
    vt.amount,
    vt.fee,
    vt.net_amount,
    vt.status,
    vt.description,
    vt.created_at,
    o.id AS order_display_id,
    o.status AS order_status
FROM vendor_transactions vt
LEFT JOIN orders o ON o.id = vt.order_id;

CREATE INDEX IF NOT EXISTS idx_mv_transaction_history_vendor ON mv_vendor_transaction_history(vendor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mv_transaction_history_type ON mv_vendor_transaction_history(transaction_type);

-- ============================================================================
-- PART 7: CREATE FUNCTIONS AND TRIGGERS
-- ============================================================================

-- 7.1 Update wallet balance on transaction insert
CREATE OR REPLACE FUNCTION fn_update_wallet_balance()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE vendor_wallets
    SET 
        balance = balance + NEW.net_amount,
        total_earned = total_earned + CASE WHEN NEW.transaction_type IN ('online_payment', 'cash_order') THEN NEW.net_amount ELSE 0 END,
        total_pending = total_pending + CASE WHEN NEW.status = 'pending' THEN NEW.net_amount ELSE 0 END,
        updated_at = NOW(),
        version = version + 1,
        last_activity_at = NOW()
    WHERE vendor_id = NEW.vendor_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate trigger
DROP TRIGGER IF EXISTS trg_update_wallet_balance ON vendor_transactions;
CREATE TRIGGER trg_update_wallet_balance
    AFTER INSERT ON vendor_transactions
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_wallet_balance();

-- 7.2 Update wallet settlement on settlement completion
CREATE OR REPLACE FUNCTION fn_update_wallet_settlement()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status = 'pending' THEN
        UPDATE vendor_wallets
        SET 
            total_settled = total_settled + NEW.net_amount,
            total_pending = total_pending - NEW.net_amount,
            balance = balance - NEW.net_amount,
            updated_at = NOW(),
            version = version + 1,
            last_activity_at = NOW()
        WHERE vendor_id = NEW.vendor_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_wallet_settlement ON vendor_settlements;
CREATE TRIGGER trg_update_wallet_settlement
    AFTER UPDATE OF status ON vendor_settlements
    FOR EACH ROW
    WHEN (NEW.status = 'completed' AND OLD.status = 'pending')
    EXECUTE FUNCTION fn_update_wallet_settlement();

-- ============================================================================
-- PART 8: ADD COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE vendor_wallets IS 'Vendor wallet tracking total balance with monetary precision (NUMERIC(12,2))';
COMMENT ON TABLE vendor_transactions IS 'Individual vendor transactions with monetary precision and audit trail';
COMMENT ON TABLE vendor_settlements IS 'Vendor settlement cycles with monetary precision and period tracking';
COMMENT ON TABLE vendor_refunds IS 'Vendor refund tracking with monetary precision and payment integration';
COMMENT ON MATERIALIZED VIEW mv_vendor_financial_summary IS 'Cached financial summary for vendor dashboard';
COMMENT ON MATERIALIZED VIEW mv_vendor_transaction_history IS 'Cached transaction history with order details';

COMMIT;