from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
import enum

class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Processing = "Processing"
    Shipped = "Shipped"
    Delivered = "Delivered"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    shipping_address = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.Pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    payment_confirmed_at = Column(DateTime, nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"))
    vendor = relationship("Vendor", back_populates="orders")

    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    item_metadata = Column(JSON, nullable=True)  
    vendor_id = Column(Integer, ForeignKey("vendor.id"))  # <- Add this line
    order_id = Column(Integer, ForeignKey("orders.id"))

    order = relationship("Order", back_populates="order_items")
    vendor = relationship("Vendor")  # Optional: Only if you want to access vendor directly from order item

