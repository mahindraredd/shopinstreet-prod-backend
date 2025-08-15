from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import UserSignup, UserOut, UserLogin, Token, UserUpdate, UserProfileOut, ShippingInfoOut, OrderOut
from app.models.models import User, ShippingDetails
from app.models.order import Order

from app.db.deps import get_db
from app.crud import user as crud_user
from app.utils.utils import verify_password, create_access_token, get_current_user
from app.schemas.schemas import ShippingInfo, ShippingInfoOut
from app.crud import shipping
from app.utils.utils import get_current_user_id




router = APIRouter()

@router.post("/signup", response_model=UserOut)
def create_user(user: UserSignup, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db=db, user_data=user)

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": db_user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email,
        "phone": db_user.phone
    }
 
 
@router.get("/{user_id}/profile", response_model=UserProfileOut)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    shipping = db.query(ShippingDetails).filter(ShippingDetails.user_id == user_id).first()
    
    print("Fetched shipping:", shipping)
    print("Type of address_type:", type(shipping.address_type) if shipping else None)
    print(f"User record: {user.__dict__}")

   

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "shipping": shipping
    }

@router.put("/{user_id}", response_model=UserOut)
def update_user_profile(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    print("Update payload received:", user_update.dict())

    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = crud_user.update_user(db, db_user, user_update)
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update user")

    return updated_user
   


@router.put("/{user_id}/shipping")
def update_shipping(user_id: int, info: ShippingInfo, db: Session = Depends(get_db)):
    if info.address_type:
        info.address_type = info.address_type.lower()
    shipping = db.query(ShippingDetails).filter(ShippingDetails.user_id == user_id).first()
    if shipping:
        for field, value in info.dict().items():
            setattr(shipping, field, value)
    else:
        shipping = ShippingDetails(user_id=user_id, **info.dict())

    db.add(shipping)
    db.commit()
    db.refresh(shipping)
    return shipping

@router.post("/shipping/add", response_model=ShippingInfoOut)
def add_address(
    data: ShippingInfo,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    return shipping.add_shipping_address(db, current_user_id, data)

@router.get("/shipping/list", response_model=List[ShippingInfoOut])
def list_addresses(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    return shipping.get_shipping_addresses(db, current_user_id)
