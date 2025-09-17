# app/models/pos_models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime, JSON, Text, DECIMAL, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
import enum

class CustomerType(str, enum.Enum):
    WALK_IN = "walk_in"
    REGULAR = "regular"
    VIP = "vip"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    
    # Customer details
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    
    # Customer categorization
    customer_type = Column(Enum(CustomerType), default=CustomerType.REGULAR)
    notes = Column(Text, nullable=True)
    
    # Vendor association
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    
    # Customer stats
    total_orders = Column(Integer, default=0)
    total_spent = Column(DECIMAL(10,2), default=0.0)
    last_visit = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    vendor = relationship("Vendor", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Discount configuration
    discount_type = Column(Enum(DiscountType), nullable=False)
    value = Column(DECIMAL(10,2), nullable=False)  # Percentage or fixed amount
    
    # Constraints
    minimum_order_amount = Column(DECIMAL(10,2), default=0.0)
    maximum_discount_amount = Column(DECIMAL(10,2), nullable=True)  # Cap for percentage discounts
    
    # Validity
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)  # Max number of uses
    used_count = Column(Integer, default=0)
    
    # Vendor association
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="discounts")

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Discount configuration
    discount_type = Column(Enum(DiscountType), nullable=False)
    value = Column(DECIMAL(10,2), nullable=False)
    
    # Constraints
    minimum_order_amount = Column(DECIMAL(10,2), default=0.0)
    maximum_discount_amount = Column(DECIMAL(10,2), nullable=True)
    
    # Validity
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    
    # Vendor association
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="promo_codes")

class TaxConfiguration(Base):
    __tablename__ = "tax_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g., "State Tax", "GST", etc.
    rate = Column(DECIMAL(5,2), nullable=False)  # Tax rate as percentage
    
    # Tax details
    description = Column(Text, nullable=True)
    tax_type = Column(String(50), default="percentage")  # percentage, fixed
    
    # Vendor association
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default tax for this vendor
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="tax_configurations")

# Add these relationships to existing models (you'll need to update them):

# In app/models/vendor.py - add these to your Vendor model:
# customers = relationship("Customer", back_populates="vendor")
# discounts = relationship("Discount", back_populates="vendor") 
# promo_codes = relationship("PromoCode", back_populates="vendor")
# tax_configurations = relationship("TaxConfiguration", back_populates="vendor")

# In app/models/order.py - add this to your Order model:
# customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
# discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=True)
# promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=True)
# customer = relationship("Customer", back_populates="orders")