# app/models/order.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime, JSON, Text, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime, JSON, Text, DECIMAL

class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Processing = "Processing"
    Shipped = "Shipped"
    Delivered = "Delivered"
    Completed = "Completed"  # NEW: For POS transactions

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Existing fields (preserved)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)  # Made nullable for POS
    customer_phone = Column(String, nullable=True)
    shipping_address = Column(String, nullable=True)  # Made nullable for POS
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.Pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Existing Razorpay fields (preserved)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    payment_confirmed_at = Column(DateTime, nullable=True)
    
    # Existing relationship (preserved)
    vendor_id = Column(Integer, ForeignKey("vendor.id"))
    vendor = relationship("Vendor", back_populates="orders")
    
    # NEW: Cashier/POS fields (will be added by migration)
    order_number = Column(String(100), unique=True, nullable=True, index=True)  # POS-YYYYMMDD-XXXXX
    order_type = Column(String(20), default="online")    # online or pos  
    payment_method = Column(String(50), default="cash")  # cash, card, digital
    payment_status = Column(String(50), default="pending")  # pending, paid, failed
    tax_amount = Column(DECIMAL(10,2), default=0.0)      # Tax calculation
    discount_amount = Column(DECIMAL(10,2), default=0.0) # Discount applied
    notes = Column(Text, nullable=True)                   # Additional notes
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_items = relationship("OrderItem", back_populates="order")
    register_session_id = Column(Integer, ForeignKey("register_sessions.id"), nullable=True)
    
    # NEW: Add relationship
    register_session = relationship("RegisterSession", back_populates="transactions")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # FIXED: Added proper foreign key constraint to products table
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    item_metadata = Column(JSON, nullable=True)  
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    # Existing relationship (preserved) 
    vendor_id = Column(Integer, ForeignKey("vendor.id"))  
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    vendor = relationship("Vendor")
    product = relationship("Product")  # This will now work with the foreign key