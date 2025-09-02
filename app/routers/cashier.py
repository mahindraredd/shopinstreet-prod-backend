# app/routers/cashier.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.deps import get_current_vendor, get_db
from app.models.product import Product, ProductPricingTier
from app.models.order import Order, OrderItem, OrderStatus
from app.models.vendor import Vendor
from datetime import datetime
import uuid
from app.models.register import RegisterSession, RegisterStatus
from sqlalchemy import desc, and_
from app.services.image_service import generate_presigned_url
from decimal import Decimal
router = APIRouter()

# Pydantic models for cashier
class CashierItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    total_price: float

class CashierCustomer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class CashierCheckout(BaseModel):
    vendor_id: int
    items: List[CashierItem]
    customer: Optional[CashierCustomer] = None
    payment_method: str = "cash"  # cash, card, digital
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    subtotal: float
    total_amount: float
    notes: Optional[str] = None

class CashierProduct(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int
    category: str
    image_url: Optional[str]
    sku: Optional[str]
    barcode: Optional[str]

class CashierDashboardResponse(BaseModel):
    products: List[CashierProduct]
    categories: List[str]
    total_products: int
    low_stock_count: int
    out_of_stock_count: int

class RegisterOpenRequest(BaseModel):
    opening_float: float = 0.0
    cashier_name: str
    register_name: str = "Main Register"
    opening_notes: Optional[str] = None

class RegisterCloseRequest(BaseModel):
    closing_amount: float
    closing_notes: Optional[str] = None

class RegisterStatusResponse(BaseModel):
    id: int
    vendor_id: int
    register_name: str
    cashier_name: str
    opening_float: float
    total_sales: float
    total_cash_sales: float
    total_card_sales: float
    total_digital_sales: float
    transaction_count: int
    status: str
    opened_at: str
    closed_at: Optional[str]
    session_duration_minutes: int


def get_price_for_quantity(product, quantity, db):
    """Get the appropriate price based on quantity from pricing tiers"""
    pricing_tiers = db.query(ProductPricingTier).filter(
        ProductPricingTier.product_id == product.id
    ).order_by(ProductPricingTier.moq.desc()).all()
    
    for tier in pricing_tiers:
        if quantity >= tier.moq:
            return tier.price
    
    if pricing_tiers:
        return pricing_tiers[-1].price
    return product.price or 0

@router.get("/cashier/dashboard/{vendor_id}", response_model=CashierDashboardResponse)
def get_cashier_dashboard(vendor_id: int, db: Session = Depends(get_db)):
    """Get all products for cashier dashboard"""
    
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get all products for this vendor
    products = db.query(Product).filter(
        Product.vendor_id == vendor_id,
        Product.is_active == True
    ).all()
    
    cashier_products = []
    categories = set()
    low_stock_count = 0
    out_of_stock_count = 0
    
    for product in products:
        # Count stock status
        if product.stock == 0:
            out_of_stock_count += 1
        elif product.stock <= 20:
            low_stock_count += 1
        # Handle image URL generation
        image_url = None
        if hasattr(product, 'image_urls') and product.image_urls and len(product.image_urls) > 0:
            # Generate presigned URL for the first image
            image_url = generate_presigned_url(product.image_urls[0])
        elif hasattr(product, 'image_url') and product.image_url:
            image_url = generate_presigned_url(product.image_url)
            
        categories.add(product.category)
        
        cashier_products.append(CashierProduct(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price or 0,
            stock=product.stock,
            category=product.category,
            image_url=image_url,  
            sku=product.sku,
            barcode=product.barcode
        ))
    
    return CashierDashboardResponse(
        products=cashier_products,
        categories=sorted(list(categories)),
        total_products=len(cashier_products),
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )

@router.get("/cashier/products/{vendor_id}")
def search_cashier_products(
    vendor_id: int,
    search: Optional[str] = None,
    category: Optional[str] = None,
    barcode: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Search products for cashier with filters"""
    
    query = db.query(Product).filter(
        Product.vendor_id == vendor_id,
        Product.is_active == True
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Product.name.ilike(search_term) |
            Product.description.ilike(search_term) |
            Product.sku.ilike(search_term)
        )
    
    if category:
        query = query.filter(Product.category == category)
        
    if barcode:
        query = query.filter(Product.barcode == barcode)
    
    products = query.limit(50).all()  # Limit for performance
    
    return [
        CashierProduct(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price or 0,
            stock=product.stock,
            category=product.category,
            image_url=getattr(product, 'image_url', None) or (product.image_urls[0] if getattr(product, 'image_urls', None) and len(product.image_urls) > 0 else None),
            sku=product.sku,
            barcode=product.barcode
        )
        for product in products
    ]

@router.get("/cashier/product/{product_id}/pricing")
def get_product_pricing(product_id: int, quantity: int, db: Session = Depends(get_db)):
    """Get pricing for a product based on quantity"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price = get_price_for_quantity(product, quantity, db)
    
    return {
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": price,
        "total_price": price * quantity,
        "available_stock": product.stock
    }

@router.post("/cashier/checkout")
def process_cashier_checkout(checkout_data: CashierCheckout, db: Session = Depends(get_db)):
    """Process a cashier checkout transaction"""
    
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == checkout_data.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get current open register session - FIXED: Ensure register_session is always defined
    register_session = db.query(RegisterSession).filter(
        and_(
            RegisterSession.vendor_id == checkout_data.vendor_id,
            RegisterSession.status == RegisterStatus.OPEN
        )
    ).first()
    
    if not register_session:
        raise HTTPException(
            status_code=400,
            detail="No register is open. Please open register before processing sales."
        )
    
    # Verify all products exist and have sufficient stock
    for item in checkout_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {item.quantity}"
            )
    
    # Generate unique order number for POS
    order_number = f"POS-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Create the order with register session link
    new_order = Order(
        order_number=order_number,
        customer_name=checkout_data.customer.name if checkout_data.customer else "Walk-in Customer",
        customer_email=checkout_data.customer.email if checkout_data.customer else None,
        customer_phone=checkout_data.customer.phone if checkout_data.customer else None,
        shipping_address="In-Store Purchase",
        total_amount=checkout_data.total_amount,
        vendor_id=checkout_data.vendor_id,
        status=OrderStatus.Completed,
        payment_method=checkout_data.payment_method,
        payment_status="paid",
        order_type="pos",
        register_session_id=register_session.id,  # Link to register session
        tax_amount=checkout_data.tax_amount,
        discount_amount=checkout_data.discount_amount,
        notes=checkout_data.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Create order items and update inventory
    for item in checkout_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        
        order_item = OrderItem(
            product_id=item.product_id,
            product_name=product.name,
            quantity=item.quantity,
            price=item.unit_price,
            vendor_id=checkout_data.vendor_id,
            order_id=new_order.id
        )
        db.add(order_item)
        
        # Update product stock
        product.stock -= item.quantity
    
    # Update register session totals - FIXED: Convert float to Decimal properly
    register_session.total_sales += Decimal(str(checkout_data.total_amount))
    register_session.transaction_count += 1
    
    if checkout_data.payment_method == "cash":
        register_session.total_cash_sales += Decimal(str(checkout_data.total_amount))
    elif checkout_data.payment_method == "card":
        register_session.total_card_sales += Decimal(str(checkout_data.total_amount))
    elif checkout_data.payment_method == "digital":
        register_session.total_digital_sales += Decimal(str(checkout_data.total_amount))
    
    db.commit()
    
    return {
        "success": True,
        "order_id": new_order.id,
        "order_number": order_number,
        "total_amount": checkout_data.total_amount,
        "payment_method": checkout_data.payment_method,
        "items_count": len(checkout_data.items),
        "register_session_id": register_session.id,
        "created_at": new_order.created_at.isoformat()
    }
@router.get("/cashier/recent-transactions/{vendor_id}")
def get_recent_pos_transactions(
    vendor_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent POS transactions for the vendor"""
    
    orders = db.query(Order).filter(
        Order.vendor_id == vendor_id,
        Order.order_type == "pos"
    ).order_by(Order.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "total_amount": order.total_amount,
            "payment_method": order.payment_method,
            "created_at": order.created_at.isoformat(),
            "items_count": len(order.order_items) if hasattr(order, 'order_items') and order.order_items else 0
        }
        for order in orders
    ]
@router.get("/cashier/register-status/{vendor_id}")
def get_register_status(vendor_id: int, db: Session = Depends(get_db)):
    """Get current register status for vendor"""
    
    # Check for open register
    open_register = db.query(RegisterSession).filter(
        and_(
            RegisterSession.vendor_id == vendor_id,
            RegisterSession.status == RegisterStatus.OPEN
        )
    ).first()
    
    if open_register:
        duration = (datetime.utcnow() - open_register.opened_at).seconds // 60
        
        return {
            "register_open": True,
            "session": RegisterStatusResponse(
                id=open_register.id,
                vendor_id=open_register.vendor_id,
                register_name=open_register.register_name,
                cashier_name=open_register.cashier_name,
                opening_float=float(open_register.opening_float),
                total_sales=float(open_register.total_sales),
                total_cash_sales=float(open_register.total_cash_sales),
                total_card_sales=float(open_register.total_card_sales),
                total_digital_sales=float(open_register.total_digital_sales),
                transaction_count=open_register.transaction_count,
                status=open_register.status.value,
                opened_at=open_register.opened_at.isoformat(),
                closed_at=open_register.closed_at.isoformat() if open_register.closed_at else None,
                session_duration_minutes=duration
            )
        }
    
    return {"register_open": False, "session": None}

@router.post("/cashier/register/open")
def open_register(
    vendor_id: int,
    request: RegisterOpenRequest,
    db: Session = Depends(get_db)
):
    """Open register for the day"""
    
    # Check if register is already open
    existing_open = db.query(RegisterSession).filter(
        and_(
            RegisterSession.vendor_id == vendor_id,
            RegisterSession.status == RegisterStatus.OPEN
        )
    ).first()
    
    if existing_open:
        raise HTTPException(
            status_code=400,
            detail=f"Register is already open since {existing_open.opened_at.strftime('%I:%M %p')}"
        )
    
    # Create new register session
    new_session = RegisterSession(
        vendor_id=vendor_id,
        register_name=request.register_name,
        cashier_name=request.cashier_name,
        opening_float=request.opening_float,
        opening_notes=request.opening_notes,
        status=RegisterStatus.OPEN
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {
        "success": True,
        "message": "Register opened successfully",
        "session_id": new_session.id,
        "opened_at": new_session.opened_at.isoformat(),
        "opening_float": float(new_session.opening_float)
    }
# Add this to your app/api/routes_order.py or app/routers/cashier.py

@router.get("/orders/{order_id}/items")
def get_order_items(
    order_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get items for a specific order"""
    
    # Verify the order belongs to this vendor
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.vendor_id == vendor.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get order items
    order_items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()
    
    return [
        {
            "id": item.id,
            "product_name": item.product_name,
            "quantity": item.quantity,
            "price": float(item.price),
            "total_price": float(item.price * item.quantity)
        }
        for item in order_items
    ]

@router.post("/cashier/register/close")
def close_register(
    vendor_id: int,
    request: RegisterCloseRequest,
    db: Session = Depends(get_db)
):
    """Close register and reconcile cash"""
    
    # Find open register
    open_register = db.query(RegisterSession).filter(
        and_(
            RegisterSession.vendor_id == vendor_id,
            RegisterSession.status == RegisterStatus.OPEN
        )
    ).first()
    
    if not open_register:
        raise HTTPException(status_code=400, detail="No register is currently open")
    
    # Calculate expected amount and variance
    expected_amount = open_register.calculate_expected_amount()
    variance = float(request.closing_amount) - expected_amount
    
    # Update register session
    open_register.closing_amount = request.closing_amount
    open_register.expected_amount = expected_amount
    open_register.variance = variance
    open_register.closing_notes = request.closing_notes
    open_register.status = RegisterStatus.CLOSED
    open_register.closed_at = datetime.utcnow()
    
    db.commit()
    
    # Calculate session summary
    session_duration = (open_register.closed_at - open_register.opened_at).seconds // 60
    
    return {
        "success": True,
        "message": "Register closed successfully",
        "session_id": open_register.id,
        "summary": {
            "session_duration_minutes": session_duration,
            "opening_float": float(open_register.opening_float),
            "total_sales": float(open_register.total_sales),
            "cash_sales": float(open_register.total_cash_sales),
            "expected_cash": expected_amount,
            "actual_cash": float(request.closing_amount),
            "variance": variance,
            "variance_status": "over" if variance > 0 else "short" if variance < 0 else "exact",
            "transaction_count": open_register.transaction_count
        }
    }

# Update your existing checkout endpoint to link to register session
# Replace your existing process_cashier_checkout with this updated version:
# Add this to main.py
# from app.routers import cashier
# app.include_router(cashier.router, prefix="/api", tags=["cashier"])