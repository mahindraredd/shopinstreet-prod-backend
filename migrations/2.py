# Migration SQL for creating the customers table
from app.db.session import engine
CUSTOMER_TABLE_SQL = """
-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id) ON DELETE CASCADE,
    
    -- Basic information
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    
    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    country VARCHAR(100) DEFAULT 'India',
    
    -- Personal details
    birthday TIMESTAMP,
    notes TEXT,
    
    -- Metrics
    total_spent DECIMAL(10,2) DEFAULT 0.00 NOT NULL,
    total_orders INTEGER DEFAULT 0 NOT NULL,
    average_order_value DECIMAL(10,2) DEFAULT 0.00 NOT NULL,
    
    -- Loyalty
    loyalty_points INTEGER DEFAULT 0 NOT NULL,
    loyalty_tier VARCHAR(20) DEFAULT 'Bronze' NOT NULL,
    
    -- Visits
    first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    visit_count INTEGER DEFAULT 1 NOT NULL,
    
    -- Preferences
    preferred_payment_method VARCHAR(20),
    marketing_consent BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_customers_vendor_id ON customers(vendor_id);
CREATE INDEX IF NOT EXISTS idx_customers_search ON customers(vendor_id, name);
CREATE INDEX IF NOT EXISTS idx_customers_contact ON customers(vendor_id, phone, email);
CREATE INDEX IF NOT EXISTS idx_customers_loyalty ON customers(vendor_id, loyalty_tier, loyalty_points);
CREATE INDEX IF NOT EXISTS idx_customers_visits ON customers(vendor_id, last_visit, visit_count);
CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(vendor_id, is_active);

-- Add customer_id to orders table if it doesn't exist
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES customers(id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
"""

with engine.connect() as connection:
    connection.execute(CUSTOMER_TABLE_SQL)
    connection.commit()
    print("Customer table created successfully!")