-- =============================================================================
-- WOMS Seed Data
-- 
-- This file contains initial seed data for lookup tables.
-- Run this after all migrations and triggers have been applied.
-- =============================================================================

-- =============================================================================
-- ACTION TYPES (Required for audit_log)
-- =============================================================================

INSERT INTO action_type (action_name, description, created_at) VALUES 
('INSERT', 'New record created', NOW()),
('UPDATE', 'Record modified', NOW()),
('DELETE', 'Record deleted', NOW()),
('SOFT_DELETE', 'Record soft deleted', NOW()),
('RESTORE', 'Record restored from soft delete', NOW()),
('LOGIN', 'User logged in', NOW()),
('LOGOUT', 'User logged out', NOW()),
('EXPORT', 'Data exported', NOW()),
('IMPORT', 'Data imported', NOW())
ON CONFLICT (action_name) DO NOTHING;

-- =============================================================================
-- STATUS (Item statuses)
-- =============================================================================

INSERT INTO status (status_name) VALUES 
('Active'),
('Inactive'),
('Discontinued'),
('Out of Stock'),
('Pending')
ON CONFLICT (status_name) DO NOTHING;

-- =============================================================================
-- ITEM TYPES
-- =============================================================================

INSERT INTO item_type (item_type_name) VALUES 
('Raw Material'),
('Finished Good'),
('Office Supplies'),
('Component'),
('Packaging'),
('Consumable')
ON CONFLICT (item_type_name) DO NOTHING;

-- =============================================================================
-- BASE UOM (Units of Measure)
-- =============================================================================

INSERT INTO base_uom (uom_name) VALUES 
('Each'),
('PCS'),
('Box'),
('Carton'),
('Kg'),
('Liter'),
('Pack'),
('Set')
ON CONFLICT (uom_name) DO NOTHING;

-- =============================================================================
-- INVENTORY TYPES
-- =============================================================================

INSERT INTO inventory_type (inventory_type_name) VALUES 
('Bulk Storage'),
('Pick Face'),
('Receiving'),
('Staging'),
('Shipping'),
('Returns')
ON CONFLICT (inventory_type_name) DO NOTHING;

-- =============================================================================
-- MOVEMENT TYPES
-- =============================================================================

INSERT INTO movement_type (movement_name) VALUES 
('Receipt'),
('Shipment'),
('Transfer'),
('Adjustment'),
('Return'),
('Cycle Count'),
('Write Off')
ON CONFLICT (movement_name) DO NOTHING;

-- =============================================================================
-- DELIVERY STATUSES
-- =============================================================================

INSERT INTO delivery_status (status_name, status_color) VALUES 
('Pending', '#FFA500'),
('Picked Up', '#2196F3'),
('In Transit', '#9C27B0'),
('Out for Delivery', '#00BCD4'),
('In Warehouse', '#FFD700'),
('Delivered', '#4CAF50'),
('Failed', '#F44336'),
('Cancelled', '#9E9E9E'),
('Return to Sender', '#FF5722'),
('Returned to Warehouse', '#795548'),
('Customer Refused', '#E91E63'),
('Address Invalid', '#607D8B')
ON CONFLICT (status_name) DO NOTHING;

-- =============================================================================
-- ROLES
-- =============================================================================

INSERT INTO roles (role_name, description, created_at) VALUES 
('Super Admin', 'Full system access', NOW()),
('Admin', 'Administrative access', NOW()),
('Manager', 'Warehouse manager', NOW()),
('Staff', 'Warehouse staff', NOW()),
('Driver', 'Delivery driver', NOW()),
('Picker', 'Order picker', NOW()),
('Packer', 'Order packer', NOW())
ON CONFLICT (role_name) DO NOTHING;

-- =============================================================================
-- PLATFORMS (Common e-commerce platforms)
-- =============================================================================

INSERT INTO platform (platform_name, is_active, created_at) VALUES 
('Shopee', TRUE, NOW()),
('Lazada', TRUE, NOW()),
('TikTok Shop', TRUE, NOW()),
('Manual', TRUE, NOW())
ON CONFLICT (platform_name) DO NOTHING;

-- =============================================================================
-- CANCELLATION REASONS
-- =============================================================================

INSERT INTO cancellation_reason (reason_code, reason_name, reason_type, requires_inspection, auto_restock, is_active, created_at) VALUES 
-- Customer-initiated
('CUSTOMER_REQUEST', 'Customer requested cancellation', 'customer', FALSE, TRUE, TRUE, NOW()),
('CUSTOMER_CHANGED_MIND', 'Customer changed mind', 'customer', FALSE, TRUE, TRUE, NOW()),
('CUSTOMER_DUPLICATE_ORDER', 'Customer duplicate order', 'customer', FALSE, TRUE, TRUE, NOW()),

-- Seller-initiated
('SELLER_CANCEL', 'Seller cancelled order', 'seller', FALSE, TRUE, TRUE, NOW()),
('OUT_OF_STOCK', 'Item out of stock', 'seller', FALSE, FALSE, TRUE, NOW()),
('PRICING_ERROR', 'Pricing error', 'seller', FALSE, TRUE, TRUE, NOW()),

-- Platform-initiated (refunds/returns)
('PLATFORM_REFUND', 'Platform refund approved', 'platform', TRUE, FALSE, TRUE, NOW()),
('PLATFORM_RETURN', 'Platform return request approved', 'platform', TRUE, FALSE, TRUE, NOW()),
('PLATFORM_DISPUTE', 'Platform dispute resolved', 'platform', TRUE, FALSE, TRUE, NOW()),

-- Delivery-related
('DELIVERY_FAILED', 'Multiple delivery attempts failed', 'delivery', TRUE, FALSE, TRUE, NOW()),
('CUSTOMER_REFUSED', 'Customer refused delivery', 'delivery', TRUE, FALSE, TRUE, NOW()),
('ADDRESS_INVALID', 'Invalid or unreachable address', 'delivery', FALSE, TRUE, TRUE, NOW()),
('CUSTOMER_UNAVAILABLE', 'Customer unavailable', 'delivery', TRUE, FALSE, TRUE, NOW()),

-- System/other
('FRAUD_SUSPECTED', 'Suspected fraudulent order', 'system', TRUE, FALSE, TRUE, NOW()),
('PAYMENT_FAILED', 'Payment verification failed', 'system', FALSE, TRUE, TRUE, NOW()),
('OTHER', 'Other reason', 'system', TRUE, FALSE, TRUE, NOW())
ON CONFLICT (reason_code) DO NOTHING;

-- =============================================================================
-- RETURN REASONS
-- =============================================================================

INSERT INTO return_reason (reason_code, reason_name, reason_type, requires_inspection, is_active, created_at) VALUES 
-- Customer-initiated returns
('WRONG_ITEM', 'Wrong item received', 'customer', TRUE, TRUE, NOW()),
('WRONG_SIZE', 'Wrong size received', 'customer', TRUE, TRUE, NOW()),
('WRONG_COLOR', 'Wrong color received', 'customer', TRUE, TRUE, NOW()),
('DAMAGED_RECEIVED', 'Item damaged on arrival', 'customer', TRUE, TRUE, NOW()),
('NOT_AS_DESCRIBED', 'Item not as described', 'customer', TRUE, TRUE, NOW()),
('CHANGED_MIND', 'Customer changed mind', 'customer', TRUE, TRUE, NOW()),
('DUPLICATE_ORDER', 'Duplicate order received', 'customer', FALSE, TRUE, NOW()),
('QUALITY_ISSUE', 'Quality does not meet expectations', 'quality', TRUE, TRUE, NOW()),

-- Platform-initiated returns
('PLATFORM_RETURN_REQUEST', 'Platform return request approved', 'platform', TRUE, TRUE, NOW()),
('PLATFORM_REFUND_APPROVED', 'Platform refund approved', 'platform', TRUE, TRUE, NOW()),
('PLATFORM_DISPUTE_RESOLVED', 'Platform dispute resolved in buyer favor', 'platform', TRUE, TRUE, NOW()),

-- Delivery-related returns
('DELIVERY_FAILED', 'Multiple delivery attempts failed', 'delivery', TRUE, TRUE, NOW()),
('CUSTOMER_REFUSED', 'Customer refused delivery', 'delivery', TRUE, TRUE, NOW()),
('UNDELIVERABLE_ADDRESS', 'Address undeliverable', 'delivery', FALSE, TRUE, NOW()),
('CUSTOMER_UNAVAILABLE', 'Customer unavailable for delivery', 'delivery', TRUE, TRUE, NOW()),
('RETURN_TO_SENDER', 'Return to sender requested', 'delivery', TRUE, TRUE, NOW()),

-- Quality-related returns
('DEFECTIVE_PRODUCT', 'Defective product', 'quality', TRUE, TRUE, NOW()),
('MANUFACTURING_DEFECT', 'Manufacturing defect', 'quality', TRUE, TRUE, NOW()),
('MISSING_PARTS', 'Missing parts or accessories', 'quality', TRUE, TRUE, NOW()),
('EXPIRED_PRODUCT', 'Product expired or near expiry', 'quality', TRUE, TRUE, NOW()),

-- Other
('OTHER_RETURN', 'Other return reason', 'customer', TRUE, TRUE, NOW())
ON CONFLICT (reason_code) DO NOTHING;

-- =============================================================================
-- EXCHANGE REASONS
-- =============================================================================

INSERT INTO exchange_reason (reason_code, reason_name, requires_return, is_active, created_at) VALUES 
-- Size/fit exchanges
('EXCHANGE_WRONG_SIZE', 'Exchange for different size', TRUE, TRUE, NOW()),
('EXCHANGE_BETTER_FIT', 'Exchange for better fit', TRUE, TRUE, NOW()),

-- Color/variant exchanges
('EXCHANGE_WRONG_COLOR', 'Exchange for different color', TRUE, TRUE, NOW()),
('EXCHANGE_DIFFERENT_VARIANT', 'Exchange for different variant', TRUE, TRUE, NOW()),

-- Quality/defect exchanges
('EXCHANGE_DEFECTIVE', 'Exchange due to defect', TRUE, TRUE, NOW()),
('EXCHANGE_DAMAGED', 'Exchange due to damage', TRUE, TRUE, NOW()),
('EXCHANGE_QUALITY_ISSUE', 'Exchange due to quality issue', TRUE, TRUE, NOW()),

-- Preference exchanges
('EXCHANGE_CUSTOMER_PREFERENCE', 'Customer preference change', TRUE, TRUE, NOW()),
('EXCHANGE_UPGRADE', 'Upgrade to better product', TRUE, TRUE, NOW()),
('EXCHANGE_DOWNGRADE', 'Downgrade to cheaper product', TRUE, TRUE, NOW()),

-- Error corrections
('EXCHANGE_WRONG_ITEM_SENT', 'Wrong item was sent', TRUE, TRUE, NOW()),
('EXCHANGE_MISSING_ITEM', 'Item was missing from order', FALSE, TRUE, NOW()),

-- Other
('EXCHANGE_OTHER', 'Other exchange reason', TRUE, TRUE, NOW())
ON CONFLICT (reason_code) DO NOTHING;
