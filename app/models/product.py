# app/models/product.py  
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    image_urls = Column(JSON, default=list)  # Store image URLs as JSON
    image_url = Column(String(512))  # Single image URL for backwards compatibility
    stock = Column(Integer, nullable=False, default=0)
    price = Column(Float, nullable=False, default=0.0)
    sku = Column(String(100), unique=True, index=True)      # Stock Keeping Unit
    barcode = Column(String(100), unique=True, index=True)  # NEW: For cashier barcode scanning
    is_active = Column(Boolean, default=True)               # Product active status
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="products")
    pricing_tiers = relationship("ProductPricingTier", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")

class ProductPricingTier(Base):
    __tablename__ = "product_pricing_tiers"

    id = Column(Integer, primary_key=True, index=True)
    moq = Column(Integer, nullable=False)  # Minimum Order Quantity
    price = Column(Float, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    product = relationship("Product", back_populates="pricing_tiers")