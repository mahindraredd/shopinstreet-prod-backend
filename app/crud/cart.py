from sqlalchemy.orm import Session
from app.models.models import CartItem
def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int, item_metadata: dict = None):
    """
    Add item to cart with proper variant handling for clothing items.
    Different size/color combinations are treated as separate cart items.
    """
    print(f"=== Backend add_to_cart called ===")
    print(f"User ID: {user_id}")
    print(f"Product ID: {product_id}")
    print(f"Quantity: {quantity}")
    print(f"Item metadata: {item_metadata}")
    
    # For clothing items, we need to check for exact variant matches
    # This includes size and color from item_metadata
    existing_item = None
    
    if item_metadata and ('selected_size' in item_metadata or 'selected_color' in item_metadata):
        # For clothing items with size/color, find exact variant match
        all_cart_items = db.query(CartItem).filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
            CartItem.status == "in_cart"
        ).all()
        
        print(f"Found {len(all_cart_items)} existing cart items for product {product_id}")
        
        # Check each cart item for exact metadata match
        for cart_item in all_cart_items:
            if cart_item.item_metadata:
                existing_metadata = cart_item.item_metadata
                print(f"Checking existing metadata: {existing_metadata}")
                
                # Check if size and color match exactly
                size_match = (
                    item_metadata.get('selected_size') == existing_metadata.get('selected_size')
                )
                color_match = (
                    item_metadata.get('selected_color') == existing_metadata.get('selected_color')
                )
                
                print(f"Size match: {size_match}, Color match: {color_match}")
                
                if size_match and color_match:
                    existing_item = cart_item
                    print(f"Found exact variant match: Cart Item ID {cart_item.id}")
                    break
    else:
        # For non-clothing items or items without size/color, use original logic
        existing_item = db.query(CartItem).filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
            CartItem.status == "in_cart"
        ).first()
        print(f"Non-clothing item logic - existing item: {existing_item.id if existing_item else None}")
    
    if existing_item:
        # Update quantity for existing variant
        print(f"Updating existing cart item {existing_item.id}")
        print(f"Old quantity: {existing_item.quantity}, Adding: {quantity}")
        existing_item.quantity += quantity
        
        # Update metadata (merge any new fields, but keep existing size/color)
        if item_metadata:
            existing_metadata = existing_item.item_metadata or {}
            # Only update non-variant fields to preserve the exact variant
            for key, value in item_metadata.items():
                if key not in ['selected_size', 'selected_color']:
                    existing_metadata[key] = value
            existing_item.item_metadata = existing_metadata
        
        db.commit()
        db.refresh(existing_item)
        print(f"Updated cart item - New quantity: {existing_item.quantity}")
        return existing_item
    else:
        # Create new cart item for new variant
        print(f"Creating new cart item for product {product_id}")
        print(f"Metadata for new item: {item_metadata}")
        
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            item_metadata=item_metadata,
            status="in_cart"
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        
        print(f"Created new cart item with ID: {cart_item.id}")
        return cart_item

def get_cart(db: Session, user_id: int):
    return db.query(CartItem).filter(CartItem.user_id == user_id).all()
