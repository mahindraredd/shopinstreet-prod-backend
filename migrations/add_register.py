# migrations/add_register_sqlalchemy.py
"""
Migration using SQLAlchemy - uses your app's existing database connection
"""
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import SessionLocal, engine

def run_migration():
    """Run the register sessions migration using SQLAlchemy"""
    
    db = SessionLocal()
    
    try:
        print("Starting register sessions migration...")
        print("Using your app's existing database connection")
        
        # Create register_sessions table
        print("Creating register_sessions table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS register_sessions (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER NOT NULL REFERENCES vendor(id) ON DELETE CASCADE,
                register_name VARCHAR(100) DEFAULT 'Main Register',
                cashier_name VARCHAR(100) NOT NULL,
                opening_float DECIMAL(10,2) NOT NULL DEFAULT 0.0,
                closing_amount DECIMAL(10,2),
                expected_amount DECIMAL(10,2),
                variance DECIMAL(10,2),
                total_sales DECIMAL(10,2) DEFAULT 0.0,
                total_cash_sales DECIMAL(10,2) DEFAULT 0.0,
                total_card_sales DECIMAL(10,2) DEFAULT 0.0,
                total_digital_sales DECIMAL(10,2) DEFAULT 0.0,
                transaction_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'closed')),
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                opening_notes TEXT,
                closing_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✅ register_sessions table created")
        
        # Add register_session_id to orders table
        print("Adding register_session_id to orders table...")
        db.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN IF NOT EXISTS register_session_id INTEGER 
            REFERENCES register_sessions(id) ON DELETE SET NULL;
        """))
        print("✅ register_session_id column added to orders")
        
        # Create indexes for performance
        print("Creating indexes...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_register_sessions_vendor_id 
            ON register_sessions(vendor_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_register_sessions_status 
            ON register_sessions(status);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_register_sessions_opened_at 
            ON register_sessions(opened_at);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_orders_register_session_id 
            ON orders(register_session_id);
        """))
        print("✅ Indexes created")
        
        # Commit all changes
        db.commit()
        
        print("\n🎉 Register sessions migration completed successfully!")
        print("\nNext steps:")
        print("1. Add RegisterSession model to app/models/register.py")
        print("2. Update Order and Vendor models with relationships")
        print("3. Add register endpoints to cashier router")
        print("4. Test the register open/close functionality")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()