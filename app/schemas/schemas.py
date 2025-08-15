from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class OrderOut(BaseModel):
    id: int
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    shipping_address: Optional[str]
    total_amount: Optional[float]
    status: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float

    class Config:
        orm_mode = True

class VendorInfo(BaseModel):
    business_name: str
    email: str
    phone: str
    owner_name: str

    class Config:
        orm_mode = True

class OrderItemInfo(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float

    class Config:
        orm_mode = True

class OrderOutWithDetails(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: str
    total_amount: float
    status: str
    created_at: datetime
    vendor: VendorInfo
    items: List[OrderItemInfo]

    class Config:
        orm_mode = True



class UserSignup(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str]
  
class AddressType(str, Enum):
    home = "Home"
    office = "Office"
    other = "Other"
    
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str]  


    class Config:
        from_attributes = True

class ShippingInfo(BaseModel):
    full_name: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    phone: str
    email: EmailStr
    address_type: AddressType = AddressType.home  # ✅ default to Home
    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    id: int
    name: str
    email: str
    phone: Optional[str] 
   
class ShippingInfoOut(BaseModel):
    full_name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    pincode: Optional[str]
    phone: Optional[str]
    email: Optional[EmailStr]
    address_type: AddressType

    

    class Config:
        orm_mode = True

class UserProfileOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str]
    shipping: Optional[ShippingInfoOut] 
 
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int
    item_metadata: Optional[Dict[str, Any]] = None  # Changed from 'metadata'

class CartItemUpdate(BaseModel):
    quantity: int
    item_metadata: Optional[Dict[str, Any]] = None  # Changed from 'metadata'

class PricingTierBase(BaseModel):
    moq: int
    price: int


class PricingTierCreate(PricingTierBase):
    pass


class PricingTierOut(PricingTierBase):
    id: int
    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    image_url: str
    available_quantity: int
    pricing_tiers: List[PricingTierCreate]


from typing import Optional

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    category: str
    image_url: str
    available_quantity: int
    price: Optional[int] = None  # Make price optional
    pricing_tiers: List[PricingTierOut]

    class Config:
        from_attributes = True



class ReviewCreate(BaseModel):
    user_id: int
    order_id: int
    product_id: int
    rating: int
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    user_id: int
    order_id: int
    product_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True