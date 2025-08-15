# app/crud/product.py - Enhanced version with metadata support

from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.product import Product, ProductPricingTier
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.product_enhanced import (
    EnhancedProductCreate, EnhancedProductOut, EnhancedProductUpdate,
    get_template_for_category
)

# ========== EXISTING FUNCTIONS (Enhanced) ==========

def create_product(db: Session, vendor_id: int, data: ProductCreate) -> Product:
    """Create a basic product (maintains backward compatibility)"""
    if not data.pricing_tiers:
        raise HTTPException(status_code=400, detail="At least one pricing tier is required")

    # Take the price from the first pricing tier
    first_price = data.pricing_tiers[0].price
    print(f"image_urls: {data.image_urls}")
    
    product = Product(
        name=data.name,
        description=data.description,
        category=data.category,
        image_urls=data.image_urls,
        stock=data.stock,
        vendor_id=vendor_id,
        price=first_price
    )
    db.add(product)
    db.flush()  # flush so product.id is available

    for tier in data.pricing_tiers:
        pricing = ProductPricingTier(
            moq=tier.moq,
            price=tier.price,
            product_id=product.id
        )
        db.add(pricing)

    db.commit()
    db.refresh(product)
    return product

# ========== NEW ENHANCED FUNCTIONS ==========

def create_enhanced_product(db: Session, vendor_id: int, data: EnhancedProductCreate, vendor_category: str) -> Product:
    """Create an enhanced product with template-specific metadata"""
    if not data.pricing_tiers:
        raise HTTPException(status_code=400, detail="At least one pricing tier is required")

    # Validate template details match vendor category
    data.validate_template_details(vendor_category)
    
    # Take the price from the first pricing tier
    first_price = data.pricing_tiers[0].get("price", data.price)
    
    # Prepare metadata fields
    clothing_details_dict = None
    food_details_dict = None
    
    if data.clothing_details:
        clothing_details_dict = data.clothing_details.model_dump()
    
    if data.food_details:
        food_details_dict = data.food_details.model_dump()
    
    product = Product(
        name=data.name,
        description=data.description,
        category=data.category,
        image_urls=data.image_urls,
        stock=data.stock,
        vendor_id=vendor_id,
        price=first_price,
        clothing_details=clothing_details_dict,  # 🆕 Clothing metadata
        food_details=food_details_dict  # 🆕 Food metadata
    )
    db.add(product)
    db.flush()

    # Add pricing tiers
    for tier in data.pricing_tiers:
        pricing = ProductPricingTier(
            moq=tier.get("moq"),
            price=tier.get("price"),
            product_id=product.id
        )
        db.add(pricing)

    db.commit()
    db.refresh(product)
    return product

def update_enhanced_product(db: Session, product_id: int, vendor_id: int, data: EnhancedProductUpdate) -> Optional[Product]:
    """Update an enhanced product with template-specific metadata"""
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return None

    # Update simple fields
    update_data = data.model_dump(exclude={"pricing_tiers", "clothing_details", "food_details"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    # Update clothing details if provided
    if data.clothing_details is not None:
        product.clothing_details = data.clothing_details.model_dump()

    # Update food details if provided
    if data.food_details is not None:
        product.food_details = data.food_details.model_dump()

    # Handle pricing tiers update if provided
    if data.pricing_tiers is not None:
        # Delete existing pricing tiers
        db.query(ProductPricingTier).filter(ProductPricingTier.product_id == product_id).delete()
        
        # Add new pricing tiers
        for tier in data.pricing_tiers:
            # Handle both dictionary and object access safely
            if isinstance(tier, dict):
                moq_value = tier.get("moq")
                price_value = tier.get("price")
            else:
                moq_value = getattr(tier, "moq", None)
                price_value = getattr(tier, "price", None)
            
            # Validate required values
            if moq_value is None:
                raise ValueError(f"Missing 'moq' in pricing tier: {tier}")
            if price_value is None:
                raise ValueError(f"Missing 'price' in pricing tier: {tier}")
            
            # Convert and validate types
            try:
                moq_int = int(moq_value)
                price_float = float(price_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid pricing tier values - moq: {moq_value}, price: {price_value}. Error: {e}")
            
            # Business validation
            if moq_int <= 0:
                raise ValueError(f"MOQ must be greater than 0, got: {moq_int}")
            if price_float <= 0:
                raise ValueError(f"Price must be greater than 0, got: {price_float}")
            
            pricing = ProductPricingTier(
                moq=moq_int,
                price=price_float,
                product_id=product_id
            )
            db.add(pricing)

    db.commit()
    db.refresh(product)
    return product

def convert_to_enhanced_product_out(product: Product, vendor_category: str) -> Dict[str, Any]:
    """Convert a Product model to EnhancedProductOut dictionary"""
    template_type = get_template_for_category(vendor_category)
    
    # Build pricing tiers
    pricing_tiers = []
    if hasattr(product, 'pricing_tiers') and product.pricing_tiers:
        pricing_tiers = [
            {"id": tier.id, "moq": tier.moq, "price": tier.price}
            for tier in product.pricing_tiers
        ]
    
    return {
        "id": product.id,
        "vendor_id": product.vendor_id,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "stock": product.stock,
        "price": product.price,
        "image_urls": product.image_urls or [],
        "created_at": product.created_at,
        "pricing_tiers": pricing_tiers,
        "template_type": template_type,
        "clothing_details": product.clothing_details,
        "food_details": product.food_details
    }

# ========== EXISTING FUNCTIONS (Unchanged) ==========

def get_products_by_vendor(db: Session, vendor_id: int, skip: int = 0, limit: int = 10):
    return db.query(Product).filter(Product.vendor_id == vendor_id).offset(skip).limit(limit).all()

def get_all_products(db: Session) -> List[Product]:
    return db.query(Product).all()

def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()

def update_product(db: Session, product_id: int, vendor_id: int, data: ProductUpdate) -> Optional[Product]:
    """Update basic product (maintains backward compatibility)"""
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return None

    # Update simple fields
    update_data = data.model_dump(exclude={"pricing_tiers"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    # Handle pricing tiers update if provided
    if data.pricing_tiers is not None:
        # Delete existing pricing tiers
        db.query(ProductPricingTier).filter(ProductPricingTier.product_id == product_id).delete()
        
        # Add new pricing tiers
        for tier in data.pricing_tiers:
            # Handle both dictionary and object access safely
            if isinstance(tier, dict):
                moq_value = tier.get("moq")
                price_value = tier.get("price")
            else:
                moq_value = getattr(tier, "moq", None)
                price_value = getattr(tier, "price", None)
            
            # Validate required values
            if moq_value is None:
                raise ValueError(f"Missing 'moq' in pricing tier: {tier}")
            if price_value is None:
                raise ValueError(f"Missing 'price' in pricing tier: {tier}")
            
            # Convert and validate types
            try:
                moq_int = int(moq_value)
                price_float = float(price_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid pricing tier values - moq: {moq_value}, price: {price_value}. Error: {e}")
            
            # Business validation
            if moq_int <= 0:
                raise ValueError(f"MOQ must be greater than 0, got: {moq_int}")
            if price_float <= 0:
                raise ValueError(f"Price must be greater than 0, got: {price_float}")
            
            pricing = ProductPricingTier(
                moq=moq_int,
                price=price_float,
                product_id=product_id
            )
            db.add(pricing)

    db.commit()
    db.refresh(product)
    return product

def delete_product(db: Session, product_id: int, vendor_id: int) -> bool:
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return False

    db.delete(product)
    db.commit()
    return True

def search_products_by_vendor(db: Session, vendor_id: int, query: str) -> List[Product]:
    return (
        db.query(Product)
        .filter(
            Product.vendor_id == vendor_id,
            (Product.name.ilike(f"%{query}%")) | (Product.category.ilike(f"%{query}%"))
        )
        .all()
    )

def update_product_images(db: Session, product_id: int, image_urls: List[str]):
    """Update product images - replaces all images with the provided list"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        # This replaces ALL images with the new list
        product.image_urls = image_urls
        db.commit()
        db.refresh(product)
    return product

# ========== METADATA-SPECIFIC FUNCTIONS ==========

def search_products_by_metadata(db: Session, vendor_id: int, metadata_filters: Dict[str, Any]) -> List[Product]:
    """Search products by metadata fields (PostgreSQL JSONB queries)"""
    query = db.query(Product).filter(Product.vendor_id == vendor_id)
    
    for key, value in metadata_filters.items():
        if key == "clothing_brand":
            query = query.filter(Product.clothing_details['brand'].astext == value)
        elif key == "food_cuisine":
            query = query.filter(Product.food_details['cuisine_type'].astext == value)
        elif key == "spice_level":
            query = query.filter(Product.food_details['spice_level'].astext == value)
        # Add more metadata filters as needed
    
    return query.all()