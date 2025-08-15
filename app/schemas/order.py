# Updated schemas in your schemas/order.py file:

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.order import OrderStatus

class RazorpayOrderCreate(BaseModel):
    amount: float
    currency: str = "INR"
    receipt: str
    notes: Optional[dict] = {}

class RazorpayOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int
    currency: str
    receipt: str
    order_data: dict

class PaymentVerification(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class OrderItemCreate(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    item_metadata: Optional[Dict[str, Any]] = None  # ADD THIS LINE

class OrderCreate(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: int
    shipping_address: str
    total_amount: float
    order_items: List[OrderItemCreate]

class OrderItemOut(OrderItemCreate):
    id: int
    item_metadata: Optional[Dict[str, Any]] = None  # ADD THIS LINE

class OrderOut(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    shipping_address: str
    total_amount: float
    status: OrderStatus
    created_at: datetime
    order_items: List[OrderItemOut]

class OrderStatusUpdate(BaseModel):
    status: str  # e.g., "pending", "processing", "shipped", "delivered"

    class Config:
        from_attributes = True