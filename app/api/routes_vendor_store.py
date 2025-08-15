from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.vendor import Vendor
from app.models.product import Product
from app.schemas.vendorstore import VendorStoreSchema, TemplateUpdateSchema, VendorStoreSchemaNormal
from app.db.deps import get_db
from app.services.image_service import generate_presigned_url, process_and_upload_images, process_and_upload_images1

router = APIRouter()

@router.get("/vendors/{vendor_id}", response_model=VendorStoreSchemaNormal)
def get_vendor_store(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
    ).first()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    products = db.query(Product).filter(Product.vendor_id == vendor.id).all()
    for product in products:
        if product.image_urls:  # Check if image_urls exists and is not empty
            product.image_urls = [
                generate_presigned_url(key) for key in product.image_urls
            ]

    categories = list(set([p.category for p in products]))
    price_range = [min([p.price for p in products]), max([p.price for p in products])] if products else [0, 0]

    return {
        "vendor_id": vendor.id,
        "business_name": vendor.business_name,
        "business_logo": vendor.business_logo,
        "categories": categories,
        "filters": {
            "priceRange": price_range,
            "availability": ["In Stock", "Out of Stock"]
        },
        "products": products,
        "template_id": vendor.template_id if hasattr(vendor, "template_id") else 1  # default to 1
    }


@router.put("/vendor/{vendor_id}/template")
def update_vendor_template(vendor_id: int, data: TemplateUpdateSchema, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Store original values to prevent auto-override
    original_template_id = data.template_id
    original_template_type = data.template_type if hasattr(data, 'template_type') else f"Template{data.template_id}"
    
    vendor.template_id = original_template_id
    vendor.template_type = original_template_type
    
    print(f"Updating vendor {vendor_id} template to {data.template_id}")
    
    # Disable auto-assignment by temporarily setting a flag or 
    # ensuring the assign_template_based_on_category method isn't called
    
    db.commit()
    
    # Verify the assignment stuck
    db.refresh(vendor)
    if vendor.template_id != original_template_id:
        # Force the assignment again if it was overridden
        vendor.template_id = original_template_id
        vendor.template_type = original_template_type
        db.commit()
        db.refresh(vendor)
    
    print(f"Vendor {vendor_id} template updated to {vendor.template_id}")
    return {"message": "Template updated successfully", "template_id": vendor.template_id}


@router.get("/vendor/store", response_model=VendorStoreSchema)
def get_vendor_store(vendor_id: int = Query(...), db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    products = db.query(Product).filter(Product.vendor_id == vendor_id).all()
    
    for product in products:
        if product.image_urls:
            product.image_urls = [generate_presigned_url(key) for key in product.image_urls]

    categories = list(set([p.category for p in products]))
    price_range = [min([p.price for p in products]), max([p.price for p in products])] if products else [0, 0]

    return {
        "vendor_id": vendor.id,
        "business_name": vendor.business_name,
        "business_logo": vendor.business_logo,
        "business_category": vendor.business_category,
        "categories": categories,
        "filters": {
            "priceRange": price_range,
            "availability": ["In Stock", "Out of Stock"]
        },
        "products": products,
        "template_id": vendor.template_id or 1  # include selected template
    }