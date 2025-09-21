# app/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.db.deps import get_current_vendor, get_db
from app.models.customer import Customer
from app.models.vendor import Vendor
from datetime import datetime, date

router = APIRouter()

# Pydantic models for customer API
class CustomerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"
    birthday: Optional[date] = None
    notes: Optional[str] = None
    preferred_payment_method: Optional[str] = None
    marketing_consent: bool = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    birthday: Optional[date] = None
    notes: Optional[str] = None
    preferred_payment_method: Optional[str] = None
    marketing_consent: Optional[bool] = None
    is_active: Optional[bool] = None

class CustomerResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str] 
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    country: Optional[str]
    birthday: Optional[date]
    notes: Optional[str]
    total_spent: float
    total_orders: int
    average_order_value: float
    loyalty_points: int
    loyalty_tier: str
    discount_percentage: float
    visit_count: int
    days_since_last_visit: int
    is_birthday_today: bool
    preferred_payment_method: Optional[str]
    marketing_consent: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

    @classmethod
    def from_customer(cls, customer: Customer):
        """Convert Customer model to CustomerResponse"""
        return cls(
            id=customer.id,
            vendor_id=customer.vendor_id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            address_line1=customer.address_line1,
            address_line2=customer.address_line2,
            city=customer.city,
            state=customer.state,
            pincode=customer.pincode,
            country=customer.country,
            birthday=customer.birthday,
            notes=customer.notes,
            total_spent=float(customer.total_spent),
            total_orders=customer.total_orders,
            average_order_value=float(customer.average_order_value),
            loyalty_points=customer.loyalty_points,
            loyalty_tier=customer.loyalty_tier,
            discount_percentage=customer.get_discount_percentage(),
            visit_count=customer.visit_count,
            days_since_last_visit=customer.days_since_last_visit(),
            is_birthday_today=customer.is_birthday_today(),
            preferred_payment_method=customer.preferred_payment_method,
            marketing_consent=customer.marketing_consent,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at
        )


@router.post("/customers", response_model=CustomerResponse)
def create_customer(
    customer_data: CustomerCreate,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    print(f"Received customer data: {customer_data.dict()}")
    print(f"Vendor ID: {vendor.id}")
    
    try:
        # Check if customer already exists by phone or email
        existing_customer = None
        if customer_data.phone:
            print(f"Checking for existing phone: {customer_data.phone}")
            existing_customer = db.query(Customer).filter(
                Customer.vendor_id == vendor.id,
                Customer.phone == customer_data.phone,
                Customer.is_active == True
            ).first()
            print(f"Existing customer by phone: {existing_customer}")
        
        if not existing_customer and customer_data.email:
            print(f"Checking for existing email: {customer_data.email}")
            existing_customer = db.query(Customer).filter(
                Customer.vendor_id == vendor.id,
                Customer.email == customer_data.email,
                Customer.is_active == True
            ).first()
            print(f"Existing customer by email: {existing_customer}")
        
        if existing_customer:
            print("Duplicate customer found, raising HTTPException")
            raise HTTPException(
                status_code=400,
                detail="Customer with this phone or email already exists"
            )
        
        # Create new customer
        print("Creating new customer...")
        new_customer = Customer(
            vendor_id=vendor.id,
            **customer_data.dict()
        )
        
        print("Adding to database...")
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        
        print(f"Customer created successfully: {new_customer.id}")
        return CustomerResponse.from_customer(new_customer)
        
    except HTTPException as e:
        print(f"HTTPException: {e.detail}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers", response_model=List[CustomerResponse])
def get_customers(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    search: Optional[str] = Query(None),
    loyalty_tier: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """Get customers with optional filtering"""
    
    query = db.query(Customer).filter(Customer.vendor_id == vendor.id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Customer.name.ilike(search_term) |
            Customer.email.ilike(search_term) |
            Customer.phone.ilike(search_term)
        )
    
    if loyalty_tier:
        query = query.filter(Customer.loyalty_tier == loyalty_tier)
    
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    
    customers = query.order_by(Customer.last_visit.desc()).offset(skip).limit(limit).all()
    return [CustomerResponse.from_customer(customer) for customer in customers]

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get customer by ID"""
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.vendor_id == vendor.id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse.from_customer(customer)

@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Update customer information"""
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.vendor_id == vendor.id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update fields
    update_data = customer_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)
    
    return CustomerResponse.from_customer(customer)

@router.delete("/customers/{customer_id}")
def deactivate_customer(
    customer_id: int,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Deactivate customer (soft delete)"""
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.vendor_id == vendor.id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.is_active = False
    customer.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Customer deactivated successfully"}

class PointsRedemptionRequest(BaseModel):
    points_to_redeem: int

@router.post("/customers/{customer_id}/redeem-points")
def redeem_customer_points(
    customer_id: int,
    request_data: PointsRedemptionRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    points_to_redeem = request_data.points_to_redeem
    """Redeem customer loyalty points"""
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.vendor_id == vendor.id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer.can_redeem_points(points_to_redeem):
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient points. Customer has {customer.loyalty_points} points"
        )
    
    discount_amount = customer.redeem_points(points_to_redeem)
    db.commit()
    
    return {
        "success": True,
        "points_redeemed": points_to_redeem,
        "discount_amount": discount_amount,
        "remaining_points": customer.loyalty_points
    }

@router.get("/customers/analytics/summary")
def get_customer_analytics(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get customer analytics summary"""
    
    customers = db.query(Customer).filter(
        Customer.vendor_id == vendor.id,
        Customer.is_active == True
    ).all()
    
    total_customers = len(customers)
    total_loyalty_points = sum(c.loyalty_points for c in customers)
    total_customer_value = sum(float(c.total_spent) for c in customers)
    
    # Tier distribution
    tier_counts = {}
    for customer in customers:
        tier = customer.loyalty_tier
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    # Recent customers (last 30 days)
    thirty_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = thirty_days_ago.replace(day=thirty_days_ago.day - 30)
    
    recent_customers = [c for c in customers if c.created_at >= thirty_days_ago]
    
    return {
        "total_customers": total_customers,
        "new_customers_this_month": len(recent_customers),
        "total_loyalty_points_issued": total_loyalty_points,
        "total_customer_lifetime_value": total_customer_value,
        "average_customer_value": total_customer_value / total_customers if total_customers > 0 else 0,
        "loyalty_tier_distribution": tier_counts,
        "top_customers": [
            {
                "id": c.id,
                "name": c.name,
                "total_spent": float(c.total_spent),
                "loyalty_tier": c.loyalty_tier,
                "total_orders": c.total_orders
            }
            for c in sorted(customers, key=lambda x: x.total_spent, reverse=True)[:10]
        ]
    }