# app/models/register.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Enum, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
import enum

class RegisterStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class RegisterSession(Base):
    __tablename__ = "register_sessions"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    
    # Register details
    register_name = Column(String(100), default="Main Register")
    cashier_name = Column(String(100), nullable=False)
    
    # Financial tracking
    opening_float = Column(DECIMAL(10,2), nullable=False, default=0.0)
    closing_amount = Column(DECIMAL(10,2), nullable=True)  # Counted cash at close
    expected_amount = Column(DECIMAL(10,2), nullable=True)  # System calculated
    variance = Column(DECIMAL(10,2), nullable=True)  # Difference (over/short)
    
    # Transaction totals for the session
    total_sales = Column(DECIMAL(10,2), default=0.0)
    total_cash_sales = Column(DECIMAL(10,2), default=0.0)
    total_card_sales = Column(DECIMAL(10,2), default=0.0)
    total_digital_sales = Column(DECIMAL(10,2), default=0.0)
    transaction_count = Column(Integer, default=0)
    
    # Status and timing
    status = Column(Enum(RegisterStatus), default=RegisterStatus.OPEN, nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    # Notes
    opening_notes = Column(Text, nullable=True)
    closing_notes = Column(Text, nullable=True)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="register_sessions")
    transactions = relationship("Order", 
                               foreign_keys="[Order.register_session_id]",
                               back_populates="register_session")

    @property
    def is_open(self):
        return self.status == RegisterStatus.OPEN
    
    @property
    def session_duration(self):
        if self.closed_at:
            return self.closed_at - self.opened_at
        return datetime.utcnow() - self.opened_at
    
    def calculate_expected_amount(self):
        """Calculate expected cash amount at close"""
        return float(self.opening_float + self.total_cash_sales)
    
    def calculate_variance(self):
        """Calculate cash variance (over/short)"""
        if self.closing_amount is not None:
            expected = self.calculate_expected_amount()
            return float(self.closing_amount) - expected
        return None