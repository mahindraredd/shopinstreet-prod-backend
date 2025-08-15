from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.models import Review
from app.schemas.schemas import ReviewCreate, ReviewOut
from app.db.deps import get_db
from typing import List

router = APIRouter()

# Existing create and get product reviews endpoints
@router.post("/", response_model=ReviewOut)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    existing = db.query(Review).filter_by(
        user_id=review.user_id,
        order_id=review.order_id,
        product_id=review.product_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this product for this order.")

    db_review = Review(**review.dict())
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/product/{product_id}", response_model=List[ReviewOut])
def get_reviews_for_product(product_id: int, db: Session = Depends(get_db)):
    return db.query(Review).filter_by(product_id=product_id).all()

# ✅ NEW: Get reviews by user ID (used by frontend)
@router.get("/user/{user_id}", response_model=List[ReviewOut])
def get_reviews_by_user(user_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter_by(user_id=user_id).all()
    if not reviews:
        return []
    return reviews

from fastapi import Path

@router.put("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    updated_data: ReviewCreate,
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter_by(id=review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.rating = updated_data.rating
    review.comment = updated_data.comment
    db.commit()
    db.refresh(review)
    return review

@router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter_by(id=review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return
