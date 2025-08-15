from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, UniqueConstraint, Enum, Float
from sqlalchemy.sql import func
import enum
from datetime import datetime
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password = Column(String)
    cart_items = relationship("CartItem", back_populates="user")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer)
    quantity = Column(Integer)
    status = Column(String, default="in_cart")
    item_metadata = Column(JSON, nullable=True)  # Changed from 'metadata' to 'item_metadata'
    
    user = relationship("User", back_populates="cart_items")

class AddressType(enum.Enum):
    home = "Home"
    office = "Office"
    other = "Other"
    
class ShippingDetails(Base):
    __tablename__ = "shipping_details"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String)        
    address = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    pincode = Column(String)
    phone = Column(String)
    email = Column(String)
    address_type = Column(Enum(AddressType), nullable=True)  

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    _table_args_ = (
        UniqueConstraint('user_id', 'order_id', 'product_id', name='unique_user_review'),
    )
    
class PendingCheckout(Base):
    __tablename__ = "pending_checkouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    razorpay_order_id = Column(String(255), unique=True, index=True)
    total_amount = Column(Float)
    shipping_info = Column(JSON)
    prepared_orders = Column(JSON)  # Store order data before payment
    cart_item_ids = Column(JSON)
    status = Column(String(50), default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)    