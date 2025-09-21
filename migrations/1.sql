-- Migration to ensure Order table has required fields for receipts
-- Run this SQL in your database to add missing fields

-- Add tax_amount if it doesn't exist
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS tax_amount DECIMAL(10,2) DEFAULT 0.00;

-- Add discount_amount if it doesn't exist  
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) DEFAULT 0.00;

-- Add notes if it doesn't exist
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Add promo_code field if you want to track which promo was used
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS promo_code VARCHAR(50);

-- Update existing orders to have 0 for tax/discount if they're NULL
UPDATE orders 
SET tax_amount = 0.00 
WHERE tax_amount IS NULL;

UPDATE orders 
SET discount_amount = 0.00 
WHERE discount_amount IS NULL;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'orders' 
AND column_name IN ('tax_amount', 'discount_amount', 'notes', 'promo_code');