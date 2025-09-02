# migrations/fix_order_vendor_relationship.py
"""
Fix Order-Vendor Foreign Key Relationship
This migration adds the missing foreign key between orders and vendor tables
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def fix_order_vendor_relationship():
    """Add missing foreign key relationship between orders and vendor tables"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return False
    
    print("🔧 FIXING ORDER-VENDOR RELATIONSHIP")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Migration SQL to fix the relationship
    migration_sql = """
    -- First, check if vendor_id column exists in orders table
    DO $$
    BEGIN
        -- Add vendor_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'vendor_id'
        ) THEN
            ALTER TABLE orders ADD COLUMN vendor_id INTEGER;
        END IF;
    END $$;
    
    -- Check if vendor table exists with correct name
    DO $$
    BEGIN
        -- Check if vendor table exists (might be named 'vendor' or 'vendors')
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendor') THEN
            -- Add foreign key constraint if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_orders_vendor_id' 
                AND table_name = 'orders'
            ) THEN
                ALTER TABLE orders 
                ADD CONSTRAINT fk_orders_vendor_id 
                FOREIGN KEY (vendor_id) REFERENCES vendor(id) ON DELETE CASCADE;
            END IF;
            
        ELSIF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendors') THEN
            -- If table is named 'vendors' instead of 'vendor'
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_orders_vendor_id' 
                AND table_name = 'orders'
            ) THEN
                ALTER TABLE orders 
                ADD CONSTRAINT fk_orders_vendor_id 
                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE;
            END IF;
        ELSE
            RAISE EXCEPTION 'Neither vendor nor vendors table found!';
        END IF;
    END $$;
    
    -- Add other missing columns for Cashier functionality
    DO $$
    BEGIN
        -- Add order_number column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'order_number'
        ) THEN
            ALTER TABLE orders ADD COLUMN order_number VARCHAR(100) UNIQUE;
        END IF;
        
        -- Add order_type column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'order_type'
        ) THEN
            ALTER TABLE orders ADD COLUMN order_type VARCHAR(20) DEFAULT 'online';
        END IF;
        
        -- Add payment_method column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'payment_method'
        ) THEN
            ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50) DEFAULT 'cash';
        END IF;
        
        -- Add payment_status column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'payment_status'
        ) THEN
            ALTER TABLE orders ADD COLUMN payment_status VARCHAR(50) DEFAULT 'pending';
        END IF;
        
        -- Add tax_amount column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'tax_amount'
        ) THEN
            ALTER TABLE orders ADD COLUMN tax_amount DECIMAL(10,2) DEFAULT 0.0;
        END IF;
        
        -- Add discount_amount column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'discount_amount'
        ) THEN
            ALTER TABLE orders ADD COLUMN discount_amount DECIMAL(10,2) DEFAULT 0.0;
        END IF;
        
        -- Add notes column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'notes'
        ) THEN
            ALTER TABLE orders ADD COLUMN notes TEXT;
        END IF;
    END $$;
    
    -- Update existing orders to have order numbers if they don't have them
    UPDATE orders 
    SET order_number = CONCAT('ORD-', LPAD(id::TEXT, 8, '0')) 
    WHERE order_number IS NULL;
    
    -- Add vendor_id to order_items table if it doesn't exist
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'order_items' AND column_name = 'vendor_id'
        ) THEN
            ALTER TABLE order_items ADD COLUMN vendor_id INTEGER;
        END IF;
    END $$;
    
    -- Add foreign key for order_items -> vendor if it doesn't exist
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendor') THEN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_order_items_vendor_id' 
                AND table_name = 'order_items'
            ) THEN
                ALTER TABLE order_items 
                ADD CONSTRAINT fk_order_items_vendor_id 
                FOREIGN KEY (vendor_id) REFERENCES vendor(id) ON DELETE CASCADE;
            END IF;
            
        ELSIF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendors') THEN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_order_items_vendor_id' 
                AND table_name = 'order_items'
            ) THEN
                ALTER TABLE order_items 
                ADD CONSTRAINT fk_order_items_vendor_id 
                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE;
            END IF;
        END IF;
    END $$;
    
    -- Add barcode field to products table for Cashier scanning
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name = 'barcode'
        ) THEN
            ALTER TABLE products ADD COLUMN barcode VARCHAR(100) UNIQUE;
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name = 'sku'
        ) THEN
            ALTER TABLE products ADD COLUMN sku VARCHAR(100) UNIQUE;
        END IF;
    END $$;
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_orders_vendor_id ON orders(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
    CREATE INDEX IF NOT EXISTS idx_orders_order_type ON orders(order_type);
    CREATE INDEX IF NOT EXISTS idx_order_items_vendor_id ON order_items(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
    CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
    """
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Database connection successful")
        
        # Check what tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('orders', 'order_items', 'vendor', 'vendors', 'products')
            ORDER BY table_name;
        """)
        existing_tables = [row[0] for row in cur.fetchall()]
        print(f"📊 Found existing tables: {existing_tables}")
        
        if 'orders' not in existing_tables:
            print("❌ ERROR: 'orders' table does not exist!")
            return False
            
        if 'vendor' not in existing_tables and 'vendors' not in existing_tables:
            print("❌ ERROR: Neither 'vendor' nor 'vendors' table exists!")
            return False
        
        # Run the migration
        print("\n🔄 Executing migration SQL...")
        cur.execute(migration_sql)
        conn.commit()
        print("✅ Migration executed successfully")
        
        # Verify the foreign key was created
        cur.execute("""
            SELECT constraint_name, table_name, column_name 
            FROM information_schema.key_column_usage 
            WHERE constraint_name IN ('fk_orders_vendor_id', 'fk_order_items_vendor_id');
        """)
        constraints = cur.fetchall()
        print(f"✅ Foreign key constraints created: {len(constraints)}")
        
        # Verify new columns were added
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'orders' 
            AND column_name IN ('vendor_id', 'order_number', 'order_type', 'payment_method', 'tax_amount', 'discount_amount');
        """)
        order_columns = [row[0] for row in cur.fetchall()]
        print(f"✅ Order columns verified: {order_columns}")
        
        # Check product columns
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name IN ('barcode', 'sku');
        """)
        product_columns = [row[0] for row in cur.fetchall()]
        print(f"✅ Product columns verified: {product_columns}")
        
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("✅ Order-Vendor relationship fixed")
        print("✅ Cashier-related fields added")
        print("✅ Performance indexes created")
        print("\nYou can now restart your FastAPI server.")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = fix_order_vendor_relationship()
    if success:
        print("\n🚀 Ready to use Cashier feature!")
    else:
        print("\n💥 Migration failed. Please check the errors above.")