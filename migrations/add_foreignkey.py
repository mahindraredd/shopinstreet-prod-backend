# migrations/simple_add_constraints.py
"""
Simple migration script without dollar-quoted functions
Adds foreign key constraints and Cashier fields
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def add_constraints_simple():
    """Add missing constraints and fields using simple SQL"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not found in .env file")
        return False
    
    print("ADDING FOREIGN KEYS AND CASHIER FIELDS")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Database connection successful")
        
        # Step 1: Check if foreign key constraint exists
        print("\n1. Checking foreign key constraints...")
        cur.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_order_items_product_id' 
            AND table_name = 'order_items';
        """)
        fk_exists = cur.fetchall()
        
        if not fk_exists:
            print("Adding foreign key constraint order_items -> products...")
            try:
                cur.execute("""
                    ALTER TABLE order_items 
                    ADD CONSTRAINT fk_order_items_product_id 
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;
                """)
                print("Foreign key constraint added successfully")
            except Exception as e:
                print(f"Warning: Could not add foreign key: {e}")
        else:
            print("Foreign key constraint already exists")
        
        # Step 2: Add order columns one by one
        print("\n2. Adding missing order columns...")
        
        order_columns_to_add = [
            ("order_number", "VARCHAR(100) UNIQUE"),
            ("order_type", "VARCHAR(20) DEFAULT 'online'"),
            ("payment_method", "VARCHAR(50) DEFAULT 'cash'"),
            ("payment_status", "VARCHAR(50) DEFAULT 'pending'"),
            ("tax_amount", "DECIMAL(10,2) DEFAULT 0.0"),
            ("discount_amount", "DECIMAL(10,2) DEFAULT 0.0"),
            ("notes", "TEXT"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_def in order_columns_to_add:
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = '{column_name}';
            """)
            column_exists = cur.fetchall()
            
            if not column_exists:
                try:
                    cur.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_def};")
                    print(f"Added column: orders.{column_name}")
                except Exception as e:
                    print(f"Warning: Could not add {column_name}: {e}")
            else:
                print(f"Column orders.{column_name} already exists")
        
        # Step 3: Add product columns
        print("\n3. Adding missing product columns...")
        
        product_columns_to_add = [
            ("barcode", "VARCHAR(100) UNIQUE"),
            ("sku", "VARCHAR(100) UNIQUE"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("image_url", "VARCHAR(512)"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_def in product_columns_to_add:
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'products' AND column_name = '{column_name}';
            """)
            column_exists = cur.fetchall()
            
            if not column_exists:
                try:
                    cur.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_def};")
                    print(f"Added column: products.{column_name}")
                except Exception as e:
                    print(f"Warning: Could not add {column_name}: {e}")
            else:
                print(f"Column products.{column_name} already exists")
        
        # Step 4: Make customer fields nullable
        print("\n4. Making customer fields nullable for POS...")
        try:
            cur.execute("ALTER TABLE orders ALTER COLUMN customer_email DROP NOT NULL;")
            cur.execute("ALTER TABLE orders ALTER COLUMN shipping_address DROP NOT NULL;")
            print("Made customer_email and shipping_address nullable")
        except Exception as e:
            print(f"Warning: Could not modify nullable constraints: {e}")
        
        # Step 5: Generate order numbers for existing orders
        print("\n5. Generating order numbers for existing orders...")
        cur.execute("SELECT COUNT(*) FROM orders WHERE order_number IS NULL;")
        orders_without_numbers = cur.fetchone()[0]
        
        if orders_without_numbers > 0:
            cur.execute("""
                UPDATE orders 
                SET order_number = CONCAT('ORD-', LPAD(id::TEXT, 8, '0')) 
                WHERE order_number IS NULL;
            """)
            print(f"Generated order numbers for {orders_without_numbers} orders")
        else:
            print("All orders already have order numbers")
        
        # Step 6: Create indexes
        print("\n6. Creating performance indexes...")
        indexes_to_create = [
            ("idx_order_items_product_id", "order_items", "product_id"),
            ("idx_orders_order_number", "orders", "order_number"),
            ("idx_orders_order_type", "orders", "order_type"),
            ("idx_products_barcode", "products", "barcode"),
            ("idx_products_sku", "products", "sku"),
            ("idx_products_is_active", "products", "is_active")
        ]
        
        for index_name, table_name, column_name in indexes_to_create:
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name});")
                print(f"Created index: {index_name}")
            except Exception as e:
                print(f"Warning: Could not create index {index_name}: {e}")
        
        # Step 7: Try to add 'Completed' status to enum
        print("\n7. Adding 'Completed' status to OrderStatus enum...")
        try:
            # Check if 'Completed' already exists in the enum
            cur.execute("""
                SELECT unnest(enum_range(NULL::orderstatus)) as status_value;
            """)
            existing_statuses = [row[0] for row in cur.fetchall()]
            
            if 'Completed' not in existing_statuses:
                cur.execute("ALTER TYPE orderstatus ADD VALUE 'Completed';")
                print("Added 'Completed' status to OrderStatus enum")
            else:
                print("'Completed' status already exists in OrderStatus enum")
        except Exception as e:
            print(f"Warning: Could not modify enum: {e}")
        
        # Commit all changes
        conn.commit()
        
        # Verification
        print("\n8. Verifying changes...")
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'orders' 
            AND column_name IN ('order_number', 'order_type', 'payment_method', 'tax_amount')
            ORDER BY column_name;
        """)
        new_order_columns = [row[0] for row in cur.fetchall()]
        
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name IN ('barcode', 'sku', 'is_active')
            ORDER BY column_name;
        """)
        new_product_columns = [row[0] for row in cur.fetchall()]
        
        print(f"Order columns added: {new_order_columns}")
        print(f"Product columns added: {new_product_columns}")
        
        print("\nMIGRATION COMPLETED SUCCESSFULLY!")
        print("You can now restart your FastAPI server")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = add_constraints_simple()
    if success:
        print("\nCashier feature is ready!")
    else:
        print("\nMigration failed. Check the errors above.")