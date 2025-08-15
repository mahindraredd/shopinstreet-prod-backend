from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db, get_current_vendor
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.schemas.schemas import OrderOutWithDetails
from app.crud import order as crud_order
from app.models.order import Order, OrderItem
from app.models.vendor import Vendor
from typing import List

router = APIRouter()

@router.post("/", response_model=OrderOut)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return crud_order.create_order(db, order_data, vendor.id)

@router.get("/mine", response_model=List[OrderOut])
def list_my_orders(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return crud_order.get_orders_by_vendor(db, vendor.id)

@router.put("/{order_id}", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    vendor = Depends(get_current_vendor)
):
    order = crud_order.update_order_status(db, order_id, status_data.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/{customer_email}", response_model=List[OrderOutWithDetails])
def get_user_orders(customer_email: str, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.customer_email == customer_email).all()

    results = []
    for order in orders:
        vendor = db.query(Vendor).filter(Vendor.id == order.vendor_id).first()
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

        results.append({
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "customer_phone": order.customer_phone,
            "shipping_address": order.shipping_address,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at,
            "vendor": {
                "business_name": vendor.business_name,
                "email": vendor.email,
                "phone": vendor.phone,
                "owner_name": vendor.owner_name,
            } if vendor else None,
            "items": [
                {
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "product_id": item.product_id
                } for item in items
            ]
        })
    return results