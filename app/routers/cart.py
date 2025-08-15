from app.schemas.schemas import UserSignup, CartItemCreate, ShippingInfo, CartItemUpdate
from app.crud import user, cart, shipping
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.order import OrderCreate, OrderItemCreate, RazorpayOrderCreate, RazorpayOrderResponse, PaymentVerification, OrderStatusUpdate
from app.models.order import Order, OrderItem, OrderStatus
from sqlalchemy import func
from app.models.models import CartItem
from app.models.product import Product, ProductPricingTier
from pydantic import BaseModel
from typing import List, Optional
from collections import defaultdict
from app.utils.utils import get_current_user_id  # Import the auth dependency
from app.services.image_service import generate_presigned_url
from app.core.config import settings
from app.models.models import PendingCheckout  # Import your new PendingCheckout model
import razorpay
import hmac
import hashlib
import uuid
import json  # Add this import for JSON parsing
from datetime import datetime
import traceback


router = APIRouter()

# New schema for checkout with selected items
class CheckoutRequest(BaseModel):
    shipping_info: ShippingInfo
    cart_item_ids: Optional[List[int]] = None  # If None, checkout all items

@router.post("/add")
def add_item(
    data: CartItemCreate, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    print(f"=== Backend add_item called ===")
    print(f"Received data: {data}")
    print(f"Product ID: {data.product_id}")
    print(f"Quantity: {data.quantity}")
    print(f"Item metadata: {data.item_metadata}")
    print(f"User ID: {current_user_id}")
    
    result = cart.add_to_cart(db, current_user_id, data.product_id, data.quantity, data.item_metadata)
    print(f"Cart operation result: {result}")
    return result

@router.post("/shipping/add", summary="Add new address")
def add_address(
    data: ShippingInfo,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    return shipping.add_shipping_address(db, current_user_id, data)

@router.get("/shipping/", summary="List all addresses")
def list_addresses(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    return shipping.get_shipping_addresses(db, current_user_id)

@router.get("/")
def get_cart_items(
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    return cart.get_cart(db, current_user_id)

def get_price_for_quantity(product, quantity, db):
    """Get the appropriate price based on quantity from pricing tiers"""
    try:
        # Get all pricing tiers for the product, ordered by moq descending
        pricing_tiers = db.query(ProductPricingTier).filter(
            ProductPricingTier.product_id == product.id
        ).order_by(ProductPricingTier.moq.desc()).all()
        
        # Find the appropriate tier based on quantity
        for tier in pricing_tiers:
            if quantity >= tier.moq:
                return float(tier.price)
        
        # If no tier matches, return the lowest tier price or default price
        if pricing_tiers:
            return float(pricing_tiers[-1].price)
        
        # Fallback to product base price if available
        return float(getattr(product, 'price', 0))
    except Exception as e:
        print(f"Error getting price for quantity: {e}")
        return 0.0

@router.get("/items")
def get_cart_items_for_checkout(
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """Get cart items with details for checkout selection"""
    try:
        cart_items = db.query(CartItem).filter(
            CartItem.user_id == current_user_id,
            CartItem.status == "in_cart"
        ).all()
        
        result = []
        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                price = get_price_for_quantity(product, item.quantity, db)
                
                # Generate presigned URLs for product images
                image_urls = []
                if product.image_urls:
                    try:
                        image_urls = [
                            generate_presigned_url(key) for key in product.image_urls
                        ]
                    except Exception as e:
                        print(f"Error generating presigned URLs: {e}")
                        image_urls = []
                
                result.append({
                    "cart_item_id": item.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "price": price,
                    "total_price": price * item.quantity,
                    "vendor_id": product.vendor_id,
                    "image_urls": image_urls,
                    "image_url": image_urls[0] if image_urls else None,
                    "item_metadata": item.item_metadata  # Changed from 'metadata'
                })
        
        for item in result:
            print(f"item_metadata: {item['item_metadata']}")
        
        return result
    except Exception as e:
        print(f"Error in get_cart_items_for_checkout: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get cart items: {str(e)}")

@router.put("/update/{item_id}")
def update_cart_item(
    item_id: int, 
    update_data: CartItemUpdate, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user_id  # Security check
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    item.quantity = update_data.quantity
    db.commit()
    db.refresh(item)
    return item

@router.delete("/remove/{item_id}")
def remove_cart_item(
    item_id: int, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user_id  # Security check
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(item)
    db.commit()
    return {"detail": "Item removed"}

# Initialize Razorpay client
try:
    razorpay_client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
except Exception as e:
    print(f"Error initializing Razorpay client: {e}")
    razorpay_client = None

@router.post("/checkout", response_model=RazorpayOrderResponse)
def checkout_create_razorpay_order(
    data: CheckoutRequest,
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """Create Razorpay order after validating cart items and calculating totals"""
    
    try:
        print(f"=== Starting checkout for user {current_user_id} ===")
        print(f"Request data: {data}")
        
        # 1. Get cart items based on selection
        query = db.query(CartItem).filter(
            CartItem.user_id == current_user_id,
            CartItem.status == "in_cart"
        )
        
        if data.cart_item_ids:
            query = query.filter(CartItem.id.in_(data.cart_item_ids))
            requested_count = len(data.cart_item_ids)
            actual_count = query.count()
            if actual_count != requested_count:
                raise HTTPException(
                    status_code=400, 
                    detail="Some selected cart items are not valid or don't belong to you"
                )
        
        cart_items = query.all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="No items selected for checkout")

        print(f"Found {len(cart_items)} cart items")

        # 2. Group cart items by vendor
        vendor_items = defaultdict(list)
        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                price = get_price_for_quantity(product, item.quantity, db)
                vendor_items[product.vendor_id].append({
                    'cart_item': item,
                    'product': product,
                    'price': price
                })

        if not vendor_items:
            raise HTTPException(status_code=400, detail="No valid products found for checkout")

        print(f"Grouped items into {len(vendor_items)} vendors")

        # 3. Calculate totals
        total_checkout_amount = 0
        total_items_count = 0
        
        prepared_orders = []  # Store order data for later creation
        
        for vendor_id, items in vendor_items.items():
            vendor_total = 0
            vendor_items_count = 0
            order_items = []
            
            for item_data in items:
                cart_item = item_data['cart_item']
                product = item_data['product']
                price = item_data['price']
                
                vendor_total += price * cart_item.quantity
                vendor_items_count += cart_item.quantity
                
                order_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": cart_item.quantity,
                    "price": price,
                    "total_price": price * cart_item.quantity,
                    "cart_item_id": cart_item.id,
                    "item_metadata": cart_item.item_metadata 
                })
            
            prepared_orders.append({
                "vendor_id": vendor_id,
                "total_amount": vendor_total,
                "items_count": vendor_items_count,
                "order_items": order_items,
                "cart_item_ids": [item_data['cart_item'].id for item_data in items]
            })
            
            total_checkout_amount += vendor_total
            total_items_count += vendor_items_count

        print(f"Total amount: {total_checkout_amount}, Total items: {total_items_count}")

        # Add shipping cost if applicable
        shipping_cost = 0  # Free shipping for now
        final_amount = total_checkout_amount + shipping_cost

        # 4. Create Razorpay order
        if not razorpay_client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")

        receipt_id = f"checkout_{current_user_id}_{uuid.uuid4().hex[:8]}"
        
        razorpay_order_data = {
            "amount": int(final_amount * 100),  # Convert to paise
            "currency": "INR",
            "receipt": receipt_id,
            "notes": {
                "user_id": str(current_user_id),
                "total_vendors": str(len(vendor_items)),
                "total_items": str(total_items_count)
            }
        }
        
        print(f"Creating Razorpay order: {razorpay_order_data}")
        
        try:
            razorpay_order = razorpay_client.order.create(data=razorpay_order_data)
            print(f"Razorpay order created: {razorpay_order}")
        except Exception as e:
            print(f"Razorpay order creation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")

        # 5. Store pending checkout data in database
        try:
            shipping_info_dict = data.shipping_info.dict()
            print(f"Shipping info dict: {shipping_info_dict}")
            
            pending_checkout = PendingCheckout(
                user_id=current_user_id,
                razorpay_order_id=razorpay_order["id"],
                total_amount=final_amount,
                shipping_info=shipping_info_dict,  # Should be stored as JSON automatically
                prepared_orders=prepared_orders,  # Should be stored as JSON automatically
                cart_item_ids=data.cart_item_ids if data.cart_item_ids else None,
                created_at=datetime.utcnow()
            )
            
            db.add(pending_checkout)
            db.commit()
            db.refresh(pending_checkout)
            print(f"Created pending checkout: {pending_checkout.id}")
            
        except Exception as e:
            print(f"Error creating pending checkout: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to store checkout data: {str(e)}")

        # 6. Return Razorpay order data to frontend
        response = RazorpayOrderResponse(
            razorpay_order_id=razorpay_order["id"],
            amount=razorpay_order["amount"],
            currency=razorpay_order["currency"],
            receipt=razorpay_order["receipt"],
            order_data={
                "pending_checkout_id": pending_checkout.id,
                "total_amount": final_amount,
                "shipping_cost": shipping_cost,
                "subtotal": total_checkout_amount,
                "total_items": total_items_count,
                "orders_to_create": len(prepared_orders),
                "shipping_info": shipping_info_dict
            }
        )
        
        print(f"Returning response: {response}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Unexpected error in checkout: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")

@router.post("/checkout/selected", response_model=RazorpayOrderResponse)
def checkout_selected_items_razorpay(
    request_data: dict,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create Razorpay order for selected cart items"""
    try:
        print(f"=== Selected checkout request ===")
        print(f"Request data: {request_data}")
        
        cart_item_ids = request_data.get("cart_item_ids", [])
        shipping_info_data = request_data.get("shipping_info", {})
        
        if not shipping_info_data:
            raise HTTPException(status_code=400, detail="shipping_info is required")
            
        if not cart_item_ids:
            raise HTTPException(status_code=400, detail="cart_item_ids is required")
        
        # Validate shipping_info has required fields
        required_fields = ['full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'country']
        missing_fields = [field for field in required_fields if field not in shipping_info_data]
        if missing_fields:
            raise HTTPException(status_code=400, detail=f"Missing required shipping fields: {missing_fields}")
        
        print(f"Creating ShippingInfo object...")
        shipping_info = ShippingInfo(**shipping_info_data)
        print(f"ShippingInfo created: {shipping_info}")
        
        checkout_request = CheckoutRequest(
            shipping_info=shipping_info,
            cart_item_ids=cart_item_ids
        )
        
        return checkout_create_razorpay_order(checkout_request, current_user_id, db)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in checkout_selected_items_razorpay: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Selected checkout failed: {str(e)}")

@router.post("/payment/verify")
def verify_payment(
    payment_data: PaymentVerification,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Verify payment and create actual orders"""
    
    try:
        print(f"Starting payment verification for user {current_user_id}")
        print(f"Payment data: {payment_data}")
        
        # 1. Verify payment signature
        print("Step 1: Verifying payment signature...")
        generated_signature = hmac.new(
            key=settings.razorpay_key_secret.encode(),
            msg=f"{payment_data.razorpay_order_id}|{payment_data.razorpay_payment_id}".encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if generated_signature != payment_data.razorpay_signature:
            print("ERROR: Payment signature mismatch!")
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        print("✓ Payment signature verified successfully")

        # 2. Get pending checkout data
        print("Step 2: Retrieving pending checkout data...")
        pending_checkout = db.query(PendingCheckout).filter(
            PendingCheckout.razorpay_order_id == payment_data.razorpay_order_id,
            PendingCheckout.user_id == current_user_id
        ).first()
        
        if not pending_checkout:
            print(f"ERROR: No pending checkout found for order_id: {payment_data.razorpay_order_id}, user_id: {current_user_id}")
            raise HTTPException(status_code=404, detail="Pending checkout not found")
        
        print(f"✓ Found pending checkout: ID {pending_checkout.id}")
        print(f"Pending checkout status: {getattr(pending_checkout, 'status', 'no_status_field')}")

        # 3. Access JSON data (should be automatically parsed if using JSON column type)
        print("Step 3: Accessing JSON data...")
        shipping_info = pending_checkout.shipping_info
        prepared_orders = pending_checkout.prepared_orders
        
        print(f"shipping_info type: {type(shipping_info)}")
        print(f"prepared_orders type: {type(prepared_orders)}")
        
        # Handle cases where JSON might not be auto-parsed
        if isinstance(shipping_info, str):
            shipping_info = json.loads(shipping_info)
        if isinstance(prepared_orders, str):
            prepared_orders = json.loads(prepared_orders)
        
        # Validate data types
        if not isinstance(shipping_info, dict):
            print(f"ERROR: shipping_info should be dict, got {type(shipping_info)}")
            print(f"shipping_info content: {shipping_info}")
            raise HTTPException(status_code=500, detail=f"Invalid shipping_info format: expected dict, got {type(shipping_info)}")
            
        if not isinstance(prepared_orders, list):
            print(f"ERROR: prepared_orders should be list, got {type(prepared_orders)}")
            print(f"prepared_orders content: {prepared_orders}")
            raise HTTPException(status_code=500, detail=f"Invalid prepared_orders format: expected list, got {type(prepared_orders)}")

        print(f"✓ Data validation passed - shipping_info keys: {list(shipping_info.keys())}")
        print(f"✓ Found {len(prepared_orders)} orders to create")

        # 4. Create shipping address
        print("Step 4: Creating shipping address...")
        try:
            shipping_address_full = f"{shipping_info['address']}, {shipping_info['city']}, {shipping_info['state']} - {shipping_info['pincode']}, {shipping_info['country']}"
            print(f"✓ Shipping address: {shipping_address_full}")
        except KeyError as e:
            print(f"Missing shipping info key: {e}")
            print(f"Available keys: {list(shipping_info.keys())}")
            raise HTTPException(status_code=500, detail=f"Missing required shipping info: {str(e)}")

         # 5. Set order status for successful payment
        print("Step 5: Setting order status...")
        # Try 'pending' first (most common for new orders)
        order_status = OrderStatus.Pending
        print(f"Using order status: '{order_status}'")

        # 6. Create actual orders
        print("Step 6: Creating orders...")
        created_orders = []
        
        for idx, order_data in enumerate(prepared_orders):
            try:
                print(f"Processing order {idx + 1}/{len(prepared_orders)}")
                print(f"Order data keys: {list(order_data.keys())}")
                
                # Validate order_data structure
                required_keys = ['vendor_id', 'total_amount', 'items_count', 'order_items', 'cart_item_ids']
                missing_keys = [key for key in required_keys if key not in order_data]
                if missing_keys:
                    raise KeyError(f"Missing required keys: {missing_keys}")
                
                # Create order for this vendor
                print(f"Creating order with status: {order_status}")
                new_order = Order(
                    customer_name=shipping_info['full_name'],
                    customer_email=shipping_info['email'],
                    customer_phone=shipping_info['phone'],
                    shipping_address=shipping_address_full,
                    total_amount=float(order_data['total_amount']),
                    vendor_id=int(order_data['vendor_id']),
                    status=order_status,  # Use the determined status
                    razorpay_order_id=payment_data.razorpay_order_id,
                    razorpay_payment_id=payment_data.razorpay_payment_id,
                    payment_confirmed_at=datetime.utcnow()
                )
                db.add(new_order)
                db.commit()
                db.refresh(new_order)
                print(f"✓ Created order ID: {new_order.id} for vendor {order_data['vendor_id']}")

                # Create OrderItems
                order_items_created = 0
                for item_data in order_data['order_items']:
                    try:
                        order_item = OrderItem(
                            product_id=int(item_data['product_id']),
                            product_name=str(item_data['product_name']),
                            quantity=int(item_data['quantity']),
                            price=float(item_data['price']),
                            vendor_id=int(order_data['vendor_id']),
                            order_id=new_order.id,
                            item_metadata=item_data.get('item_metadata') 
                        )
                        db.add(order_item)
                        order_items_created += 1
                    except Exception as e:
                        print(f"Error creating order item: {e}")
                        print(f"Item data: {item_data}")
                        raise
                
                print(f"✓ Created {order_items_created} order items")

                # Update cart item statuses
                cart_item_ids = order_data.get('cart_item_ids', [])
                if cart_item_ids:
                    updated_count = db.query(CartItem).filter(
                        CartItem.id.in_(cart_item_ids),
                        CartItem.user_id == current_user_id
                    ).update({"status": "checkout"}, synchronize_session=False)
                    print(f"✓ Updated {updated_count} cart items to 'ordered' status")

                # Add to created orders list
                created_orders.append({
                    "order_id": new_order.id,
                    "vendor_id": order_data['vendor_id'],
                    "total_amount": order_data['total_amount'],
                    "items_count": order_data['items_count'],
                    "customer_name": shipping_info['full_name'],
                    "customer_email": shipping_info['email'],
                    "customer_phone": shipping_info['phone'],
                    "shipping_address": shipping_address_full,
                    "order_items": order_data['order_items'],
                    "status": str(order_status),  # Convert to string for JSON response
                    "created_at": new_order.created_at.isoformat() if hasattr(new_order, 'created_at') else datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                print(f"Error processing order {idx + 1}: {e}")
                print(f"Order data: {order_data}")
                print(f"Full traceback:\n{traceback.format_exc()}")
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to create order {idx + 1}: {str(e)}")

        # 7. Mark pending checkout as completed
        print("Step 7: Finalizing checkout...")
        if hasattr(pending_checkout, 'status'):
            pending_checkout.status = "completed"
        if hasattr(pending_checkout, 'completed_at'):
            pending_checkout.completed_at = datetime.utcnow()
        
        db.commit()
        print("✓ All database changes committed successfully")

        # 8. Return success response
        response_data = {
            "success": True,
            "message": "Payment verified and orders created successfully",
            "order_data": {
                "total_amount": float(pending_checkout.total_amount),
                "orders_created": len(created_orders),
                "orders": created_orders,
                "shipping_info": shipping_info,
                "payment_id": payment_data.razorpay_payment_id,
                "order_date": datetime.utcnow().isoformat()
            }
        }
        
        print(f"✓ Payment verification completed. Created {len(created_orders)} orders.")
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"UNEXPECTED ERROR in payment verification: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        
        # Rollback any pending changes
        try:
            db.rollback()
            print("✓ Database rolled back")
        except Exception as rollback_error:
            print(f"! Failed to rollback database: {rollback_error}")
            
        raise HTTPException(
            status_code=500, 
            detail=f"Payment verification failed: {str(e)}"
        )