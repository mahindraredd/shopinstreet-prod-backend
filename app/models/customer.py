# app/models/customer.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from datetime import datetime
from typing import Optional

class Customer(Base):
    __tablename__ = "customers"

    # Primary key and vendor relationship
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False, index=True)

    # Basic customer information
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    
    # Address information (optional)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India")
    
    # Personal details
    birthday = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Customer metrics
    total_spent = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    average_order_value = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Loyalty information
    loyalty_points = Column(Integer, default=0, nullable=False)
    loyalty_tier = Column(String(20), default="Bronze", nullable=False)  # Bronze, Silver, Gold, Platinum
    
    # Visit tracking
    first_visit = Column(DateTime, default=func.now(), nullable=False)
    last_visit = Column(DateTime, default=func.now(), nullable=False)
    visit_count = Column(Integer, default=1, nullable=False)
    
    # Customer preferences
    preferred_payment_method = Column(String(20), nullable=True)  # cash, card, digital
    marketing_consent = Column(Boolean, default=True, nullable=False)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    vendor = relationship("Vendor", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

    # Indexes for performance
    __table_args__ = (
        Index('idx_customer_search', 'vendor_id', 'name'),
        Index('idx_customer_contact', 'vendor_id', 'phone', 'email'),
        Index('idx_customer_loyalty', 'vendor_id', 'loyalty_tier', 'loyalty_points'),
        Index('idx_customer_visits', 'vendor_id', 'last_visit', 'visit_count'),
    )

    def calculate_loyalty_tier(self):
        """Calculate customer loyalty tier based on total spent"""
        if self.total_spent >= 50000:  # ₹50,000+
            return "Platinum"
        elif self.total_spent >= 25000:  # ₹25,000+
            return "Gold"
        elif self.total_spent >= 10000:  # ₹10,000+
            return "Silver"
        else:
            return "Bronze"
    
    def update_metrics(self, new_order_amount: float):
        """Update customer metrics after a new purchase"""
        from decimal import Decimal
        
        self.total_orders += 1
        # Convert float to Decimal to match database column type
        self.total_spent += Decimal(str(new_order_amount))
        self.average_order_value = self.total_spent / self.total_orders
        self.last_visit = datetime.utcnow()
        self.visit_count += 1
    
        # Update loyalty points (1 point per ₹10 spent)
        points_earned = int(new_order_amount / 10)
        self.loyalty_points += points_earned
        
        # Update loyalty tier
        self.loyalty_tier = self.calculate_loyalty_tier()
        
        return points_earned
    
    
    def get_discount_percentage(self) -> float:
        """Get discount percentage based on loyalty tier"""
        tier_discounts = {
            "Bronze": 0.0,      # 0% discount
            "Silver": 2.5,      # 2.5% discount
            "Gold": 5.0,        # 5% discount  
            "Platinum": 7.5     # 7.5% discount
        }
        return tier_discounts.get(self.loyalty_tier, 0.0)
    
    def can_redeem_points(self, points_to_redeem: int) -> bool:
        """Check if customer can redeem specified points"""
        return self.loyalty_points >= points_to_redeem
    
    def redeem_points(self, points_to_redeem: int) -> float:
        """Redeem points for discount amount (₹1 = 10 points)"""
        if self.can_redeem_points(points_to_redeem):
            discount_amount = points_to_redeem / 10  # 10 points = ₹1
            self.loyalty_points -= points_to_redeem
            return discount_amount
        return 0.0
    
    def get_full_address(self) -> str:
        """Get formatted full address"""
        address_parts = []
        if self.address_line1:
            address_parts.append(self.address_line1)
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city:
            address_parts.append(self.city)
        if self.state:
            address_parts.append(self.state)
        if self.pincode:
            address_parts.append(self.pincode)
        
        return ", ".join(address_parts) if address_parts else ""
    
    def is_birthday_today(self) -> bool:
        """Check if today is customer's birthday"""
        if not self.birthday:
            return False
        
        today = datetime.now().date()
        birthday = self.birthday.date()
        return (today.month == birthday.month and today.day == birthday.day)
    
    def days_since_last_visit(self) -> int:
        """Get number of days since last visit"""
        if not self.last_visit:
            return 0
        
        return (datetime.utcnow() - self.last_visit).days
    
    def to_dict(self):
        """Convert customer to dictionary for API responses"""
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.get_full_address(),
            "birthday": self.birthday.isoformat() if self.birthday else None,
            "notes": self.notes,
            "total_spent": float(self.total_spent),
            "total_orders": self.total_orders,
            "average_order_value": float(self.average_order_value),
            "loyalty_points": self.loyalty_points,
            "loyalty_tier": self.loyalty_tier,
            "discount_percentage": self.get_discount_percentage(),
            "first_visit": self.first_visit.isoformat() if self.first_visit else None,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
            "visit_count": self.visit_count,
            "preferred_payment_method": self.preferred_payment_method,
            "is_birthday_today": self.is_birthday_today(),
            "days_since_last_visit": self.days_since_last_visit(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', phone='{self.phone}', tier='{self.loyalty_tier}')>"


# Replace your CUSTOMER_TABLE_SQL in main.py with this:
CUSTOMER_MIGRATION_SQL = """
-- Add missing columns to existing customers table
ALTER TABLE customers ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS pincode VARCHAR(10);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'India';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS birthday TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_spent DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_orders INTEGER DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS average_order_value DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS loyalty_points INTEGER DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS loyalty_tier VARCHAR(20) DEFAULT 'Bronze';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_payment_method VARCHAR(20);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN DEFAULT TRUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create indexes if they don't exist
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
