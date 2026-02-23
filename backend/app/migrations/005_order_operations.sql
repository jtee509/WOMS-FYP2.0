-- =============================================================================
-- WOMS Order Operations Tables
-- 
-- This file contains tables for order returns, exchanges, modifications,
-- and price adjustments with full audit trails.
--
-- Run this after 004_seed_data.sql has been applied.
--
-- Tables:
-- 1. return_reason - Lookup table for return reasons
-- 2. order_returns - Tracks return workflow and inspection
-- 3. exchange_reason - Lookup table for exchange reasons
-- 4. order_exchanges - Tracks exchange relationships and value adjustments
-- 5. order_modifications - Full audit trail for order changes
-- 6. order_price_adjustments - Tracks top-ups, reductions, waivers
-- =============================================================================

-- =============================================================================
-- 1. RETURN REASON LOOKUP TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS return_reason (
    reason_id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) UNIQUE NOT NULL,
    reason_name VARCHAR(200) NOT NULL,
    reason_type VARCHAR(50) NOT NULL CHECK (reason_type IN ('customer', 'platform', 'delivery', 'quality')),
    requires_inspection BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE return_reason IS 'Lookup table for order return reasons';
COMMENT ON COLUMN return_reason.reason_type IS 'Type: customer, platform, delivery, quality';
COMMENT ON COLUMN return_reason.requires_inspection IS 'Whether returned items need QC inspection before restocking';

-- Index for common lookups
CREATE INDEX IF NOT EXISTS idx_return_reason_code ON return_reason(reason_code);
CREATE INDEX IF NOT EXISTS idx_return_reason_type ON return_reason(reason_type);
CREATE INDEX IF NOT EXISTS idx_return_reason_active ON return_reason(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- 2. ORDER RETURNS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS order_returns (
    id SERIAL PRIMARY KEY,
    
    -- Order references
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    order_detail_id INTEGER NOT NULL REFERENCES order_details(detail_id) ON DELETE RESTRICT,
    
    -- Return classification
    return_type VARCHAR(50) NOT NULL CHECK (return_type IN ('customer_return', 'delivery_failed', 'platform_return', 'quality_issue')),
    return_reason_id INTEGER REFERENCES return_reason(reason_id),
    
    -- Return workflow status
    return_status VARCHAR(50) NOT NULL DEFAULT 'requested' CHECK (
        return_status IN ('requested', 'approved', 'rejected', 'in_transit', 'received', 'inspecting', 'completed', 'cancelled')
    ),
    
    -- Quantity tracking
    returned_quantity INTEGER NOT NULL DEFAULT 1 CHECK (returned_quantity > 0),
    
    -- Inspection workflow
    inspection_status VARCHAR(50) DEFAULT 'pending' CHECK (
        inspection_status IN ('pending', 'passed', 'failed', 'partial')
    ),
    inspection_notes TEXT,
    inspected_at TIMESTAMP,
    inspected_by_user_id INTEGER REFERENCES users(user_id),
    
    -- Restock decision after inspection
    restock_decision VARCHAR(50) CHECK (
        restock_decision IN ('restock', 'dispose', 'repair', 'exchange', 'pending')
    ),
    restocked_quantity INTEGER DEFAULT 0,
    restocked_at TIMESTAMP,
    
    -- Platform integration
    platform_return_reference VARCHAR(200),
    
    -- Audit trail
    initiated_by_user_id INTEGER REFERENCES users(user_id),
    notes TEXT,
    
    -- Timestamps
    requested_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    received_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE order_returns IS 'Tracks order return workflow including inspection and restocking';
COMMENT ON COLUMN order_returns.return_type IS 'Type: customer_return, delivery_failed, platform_return, quality_issue';
COMMENT ON COLUMN order_returns.return_status IS 'Workflow: requested -> approved -> in_transit -> received -> inspecting -> completed';
COMMENT ON COLUMN order_returns.inspection_status IS 'QC result: pending, passed, failed, partial';
COMMENT ON COLUMN order_returns.restock_decision IS 'Post-inspection: restock, dispose, repair, exchange';

-- Indexes for order_returns
CREATE INDEX IF NOT EXISTS idx_order_returns_order_id ON order_returns(order_id);
CREATE INDEX IF NOT EXISTS idx_order_returns_detail_id ON order_returns(order_detail_id);
CREATE INDEX IF NOT EXISTS idx_order_returns_status ON order_returns(return_status);
CREATE INDEX IF NOT EXISTS idx_order_returns_type ON order_returns(return_type);
CREATE INDEX IF NOT EXISTS idx_order_returns_inspection ON order_returns(inspection_status);
CREATE INDEX IF NOT EXISTS idx_order_returns_platform_ref ON order_returns(platform_return_reference) WHERE platform_return_reference IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_returns_requested_at ON order_returns(requested_at);

-- =============================================================================
-- 3. EXCHANGE REASON LOOKUP TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS exchange_reason (
    reason_id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) UNIQUE NOT NULL,
    reason_name VARCHAR(200) NOT NULL,
    requires_return BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE exchange_reason IS 'Lookup table for order exchange reasons';
COMMENT ON COLUMN exchange_reason.requires_return IS 'Whether original item must be returned for exchange';

-- Index for common lookups
CREATE INDEX IF NOT EXISTS idx_exchange_reason_code ON exchange_reason(reason_code);
CREATE INDEX IF NOT EXISTS idx_exchange_reason_active ON exchange_reason(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- 4. ORDER EXCHANGES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS order_exchanges (
    id SERIAL PRIMARY KEY,
    
    -- Original order/item references
    original_order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    original_detail_id INTEGER NOT NULL REFERENCES order_details(detail_id) ON DELETE RESTRICT,
    
    -- Exchange classification
    exchange_type VARCHAR(50) NOT NULL CHECK (exchange_type IN ('same_value', 'different_value', 'in_place')),
    exchange_reason_id INTEGER REFERENCES exchange_reason(reason_id),
    
    -- Exchange workflow status
    exchange_status VARCHAR(50) NOT NULL DEFAULT 'requested' CHECK (
        exchange_status IN ('requested', 'approved', 'processing', 'shipped', 'completed', 'cancelled')
    ),
    
    -- For linked exchanges (new order created)
    new_order_id INTEGER REFERENCES orders(order_id),
    new_detail_id INTEGER REFERENCES order_details(detail_id),
    
    -- For in-place exchanges (same order modified)
    exchanged_item_id INTEGER REFERENCES items(item_id),
    exchanged_quantity INTEGER DEFAULT 1 CHECK (exchanged_quantity > 0),
    
    -- Value adjustment tracking
    original_value FLOAT DEFAULT 0,
    new_value FLOAT DEFAULT 0,
    value_difference FLOAT DEFAULT 0,
    adjustment_status VARCHAR(50) DEFAULT 'pending' CHECK (
        adjustment_status IN ('pending', 'paid', 'waived', 'credited', 'not_applicable')
    ),
    
    -- Link to return record if original item needs to come back
    return_id INTEGER REFERENCES order_returns(id),
    
    -- Platform integration
    platform_exchange_reference VARCHAR(200),
    
    -- Audit trail
    initiated_by_user_id INTEGER REFERENCES users(user_id),
    approved_by_user_id INTEGER REFERENCES users(user_id),
    notes TEXT,
    
    -- Timestamps
    requested_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE order_exchanges IS 'Tracks order exchange relationships and value adjustments';
COMMENT ON COLUMN order_exchanges.exchange_type IS 'Type: same_value (equal swap), different_value (price difference), in_place (modify existing)';
COMMENT ON COLUMN order_exchanges.exchange_status IS 'Workflow: requested -> approved -> processing -> shipped -> completed';
COMMENT ON COLUMN order_exchanges.value_difference IS 'Positive = customer pays more, Negative = credit/refund';
COMMENT ON COLUMN order_exchanges.adjustment_status IS 'Payment status: pending, paid, waived, credited, not_applicable';

-- Indexes for order_exchanges
CREATE INDEX IF NOT EXISTS idx_order_exchanges_original_order ON order_exchanges(original_order_id);
CREATE INDEX IF NOT EXISTS idx_order_exchanges_original_detail ON order_exchanges(original_detail_id);
CREATE INDEX IF NOT EXISTS idx_order_exchanges_new_order ON order_exchanges(new_order_id) WHERE new_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_exchanges_status ON order_exchanges(exchange_status);
CREATE INDEX IF NOT EXISTS idx_order_exchanges_type ON order_exchanges(exchange_type);
CREATE INDEX IF NOT EXISTS idx_order_exchanges_return ON order_exchanges(return_id) WHERE return_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_exchanges_platform_ref ON order_exchanges(platform_exchange_reference) WHERE platform_exchange_reference IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_exchanges_requested_at ON order_exchanges(requested_at);

-- =============================================================================
-- 5. ORDER MODIFICATIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS order_modifications (
    id SERIAL PRIMARY KEY,
    
    -- Order references
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    order_detail_id INTEGER REFERENCES order_details(detail_id),
    
    -- Modification classification
    modification_type VARCHAR(50) NOT NULL CHECK (
        modification_type IN ('address', 'recipient', 'item_add', 'item_remove', 'item_change', 'quantity', 'pricing', 'shipping', 'other')
    ),
    
    -- Field-level tracking
    field_changed VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    
    -- Reason for modification
    modification_reason TEXT,
    
    -- Related records (if modification triggered by exchange/return)
    related_exchange_id INTEGER REFERENCES order_exchanges(id),
    related_return_id INTEGER REFERENCES order_returns(id),
    
    -- Audit trail
    modified_by_user_id INTEGER REFERENCES users(user_id),
    modified_at TIMESTAMP DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE order_modifications IS 'Full audit trail for all order changes';
COMMENT ON COLUMN order_modifications.modification_type IS 'Type: address, recipient, item_add, item_remove, item_change, quantity, pricing, shipping, other';
COMMENT ON COLUMN order_modifications.field_changed IS 'Specific field that was changed (e.g., shipping_address, resolved_item_id, quantity)';
COMMENT ON COLUMN order_modifications.old_value IS 'Previous value stored as JSONB for flexibility';
COMMENT ON COLUMN order_modifications.new_value IS 'New value stored as JSONB for flexibility';

-- Indexes for order_modifications
CREATE INDEX IF NOT EXISTS idx_order_modifications_order_id ON order_modifications(order_id);
CREATE INDEX IF NOT EXISTS idx_order_modifications_detail_id ON order_modifications(order_detail_id) WHERE order_detail_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_modifications_type ON order_modifications(modification_type);
CREATE INDEX IF NOT EXISTS idx_order_modifications_field ON order_modifications(field_changed);
CREATE INDEX IF NOT EXISTS idx_order_modifications_user ON order_modifications(modified_by_user_id);
CREATE INDEX IF NOT EXISTS idx_order_modifications_date ON order_modifications(modified_at);
CREATE INDEX IF NOT EXISTS idx_order_modifications_exchange ON order_modifications(related_exchange_id) WHERE related_exchange_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_modifications_return ON order_modifications(related_return_id) WHERE related_return_id IS NOT NULL;

-- GIN index for JSONB searches
CREATE INDEX IF NOT EXISTS idx_order_modifications_old_value ON order_modifications USING GIN (old_value);
CREATE INDEX IF NOT EXISTS idx_order_modifications_new_value ON order_modifications USING GIN (new_value);

-- =============================================================================
-- 6. ORDER PRICE ADJUSTMENTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS order_price_adjustments (
    id SERIAL PRIMARY KEY,
    
    -- Order references
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    order_detail_id INTEGER REFERENCES order_details(detail_id),
    
    -- Adjustment classification
    adjustment_type VARCHAR(50) NOT NULL CHECK (
        adjustment_type IN ('top_up', 'reduction', 'waived', 'exchange_difference', 'discount', 'fee', 'correction')
    ),
    
    -- Adjustment details
    adjustment_reason TEXT NOT NULL,
    original_amount FLOAT NOT NULL DEFAULT 0,
    adjustment_amount FLOAT NOT NULL DEFAULT 0,
    final_amount FLOAT NOT NULL DEFAULT 0,
    
    -- Related records
    related_exchange_id INTEGER REFERENCES order_exchanges(id),
    related_modification_id INTEGER REFERENCES order_modifications(id),
    
    -- Workflow status
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'applied', 'cancelled', 'refunded')
    ),
    
    -- Audit trail
    created_by_user_id INTEGER REFERENCES users(user_id),
    applied_by_user_id INTEGER REFERENCES users(user_id),
    applied_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE order_price_adjustments IS 'Tracks order price adjustments including top-ups, reductions, and waivers';
COMMENT ON COLUMN order_price_adjustments.adjustment_type IS 'Type: top_up (customer pays more), reduction (customer pays less), waived (no charge), exchange_difference, discount, fee, correction';
COMMENT ON COLUMN order_price_adjustments.adjustment_amount IS 'Positive = increase, Negative = decrease';
COMMENT ON COLUMN order_price_adjustments.status IS 'Workflow: pending -> applied/cancelled/refunded';

-- Indexes for order_price_adjustments
CREATE INDEX IF NOT EXISTS idx_order_price_adj_order_id ON order_price_adjustments(order_id);
CREATE INDEX IF NOT EXISTS idx_order_price_adj_detail_id ON order_price_adjustments(order_detail_id) WHERE order_detail_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_price_adj_type ON order_price_adjustments(adjustment_type);
CREATE INDEX IF NOT EXISTS idx_order_price_adj_status ON order_price_adjustments(status);
CREATE INDEX IF NOT EXISTS idx_order_price_adj_exchange ON order_price_adjustments(related_exchange_id) WHERE related_exchange_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_price_adj_modification ON order_price_adjustments(related_modification_id) WHERE related_modification_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_price_adj_created_at ON order_price_adjustments(created_at);

-- =============================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- =============================================================================

-- Trigger function for updated_at (reuse if exists from 001_triggers.sql)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to new tables
DROP TRIGGER IF EXISTS update_order_returns_updated_at ON order_returns;
CREATE TRIGGER update_order_returns_updated_at
    BEFORE UPDATE ON order_returns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_order_exchanges_updated_at ON order_exchanges;
CREATE TRIGGER update_order_exchanges_updated_at
    BEFORE UPDATE ON order_exchanges
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_order_price_adjustments_updated_at ON order_price_adjustments;
CREATE TRIGGER update_order_price_adjustments_updated_at
    BEFORE UPDATE ON order_price_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TRIGGER: Auto-update order_details return fields from order_returns
-- =============================================================================

CREATE OR REPLACE FUNCTION sync_order_detail_return_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Update order_details return_status and returned_quantity when order_returns changes
    UPDATE order_details
    SET 
        return_status = NEW.return_status,
        returned_quantity = NEW.returned_quantity,
        updated_at = NOW()
    WHERE detail_id = NEW.order_detail_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_return_status_trigger ON order_returns;
CREATE TRIGGER sync_return_status_trigger
    AFTER INSERT OR UPDATE ON order_returns
    FOR EACH ROW
    EXECUTE FUNCTION sync_order_detail_return_status();

-- =============================================================================
-- TRIGGER: Auto-calculate value_difference for exchanges
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_exchange_value_difference()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-calculate value_difference
    NEW.value_difference = COALESCE(NEW.new_value, 0) - COALESCE(NEW.original_value, 0);
    
    -- Set adjustment_status based on value_difference
    IF NEW.value_difference = 0 THEN
        NEW.adjustment_status = 'not_applicable';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calc_exchange_value_diff_trigger ON order_exchanges;
CREATE TRIGGER calc_exchange_value_diff_trigger
    BEFORE INSERT OR UPDATE ON order_exchanges
    FOR EACH ROW
    EXECUTE FUNCTION calculate_exchange_value_difference();

-- =============================================================================
-- TRIGGER: Auto-calculate final_amount for price adjustments
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_price_adjustment_final()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-calculate final_amount
    NEW.final_amount = COALESCE(NEW.original_amount, 0) + COALESCE(NEW.adjustment_amount, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calc_price_adjustment_final_trigger ON order_price_adjustments;
CREATE TRIGGER calc_price_adjustment_final_trigger
    BEFORE INSERT OR UPDATE ON order_price_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION calculate_price_adjustment_final();

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- List all new tables
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN ('return_reason', 'order_returns', 'exchange_reason', 'order_exchanges', 'order_modifications', 'order_price_adjustments');

-- Check constraints
-- SELECT conname, contype, pg_get_constraintdef(oid) 
-- FROM pg_constraint 
-- WHERE conrelid IN ('order_returns'::regclass, 'order_exchanges'::regclass, 'order_modifications'::regclass, 'order_price_adjustments'::regclass);
