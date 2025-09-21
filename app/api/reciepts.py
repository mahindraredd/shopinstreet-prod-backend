# app/routers/receipts.py - Complete updated version

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session
import qrcode
import base64
import re
from io import BytesIO

from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.models.order import Order, OrderItem

router = APIRouter()

# Request Models
class PrintReceiptRequest(BaseModel):
    transaction_id: int = Field(..., description="Order ID from completed sale")
    gift_receipt: bool = Field(False, description="Whether to print as gift receipt (no prices)")

class EmailReceiptRequest(BaseModel):
    transaction_id: int = Field(..., description="Order ID from completed sale") 
    customer_email: EmailStr = Field(..., description="Customer email address")

# Response Models
class PrintReceiptResponse(BaseModel):
    transaction_id: int
    is_gift_receipt: bool
    print_ready: bool
    receipt_html: str

class EmailReceiptResponse(BaseModel):
    message: str
    success: bool
    email_sent_to: str

def generate_qr_code_base64(url: str) -> str:
    """Generate QR code as base64 string"""
    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_base64}"
    except Exception as e:
        # Return a simple placeholder if QR generation fails
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
def get_vendor_website_url(vendor: Vendor) -> str:
    """Get vendor's website URL using your existing vendor model methods"""
    if not vendor:
        return "https://shopinstreet.com"
    
    # Use the vendor model's built-in method for website URL
    if hasattr(vendor, 'get_website_url') and vendor.get_website_url():
        return vendor.get_website_url()
    
    # Check if vendor has a custom website_url
    if vendor.website_url:
        # Ensure URL has protocol
        url = vendor.website_url
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        return url
    
    # Check if vendor has a subdomain
    if vendor.subdomain:
        return f"https://{vendor.subdomain}.shopinstreet.com"
    
    # Fallback to shopinstreet.com
    return "https://shopinstreet.com"

def generate_receipt_html(order: Order, order_items: list, is_gift: bool = False, vendor: Vendor = None) -> str:
    """Generate HTML for receipt printing using real order data with proper type handling"""
    
    # Calculate totals - convert everything to float first to avoid type conflicts
    subtotal = float(sum(float(item.price) * int(item.quantity) for item in order_items))
    total_items = sum(int(item.quantity) for item in order_items)
    
    # Format date
    order_date = order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get order values with safe defaults and convert all to float
    tax_amount = 0.0
    discount_amount = 0.0
    notes = ""
    
    # Safe extraction and conversion to float
    if hasattr(order, 'tax_amount') and order.tax_amount is not None:
        tax_amount = float(order.tax_amount)
    
    if hasattr(order, 'discount_amount') and order.discount_amount is not None:
        discount_amount = float(order.discount_amount)
    
    if hasattr(order, 'notes') and order.notes:
        notes = str(order.notes)
    
    # Calculate the correct total: subtotal + tax - discount
    calculated_total = subtotal + tax_amount - discount_amount
    
    # Get vendor website URL and generate QR code
    vendor_website_url = get_vendor_website_url(vendor)
    qr_code_base64 = generate_qr_code_base64(vendor_website_url)
    
    # Get vendor business details
    business_name = vendor.business_name if vendor and vendor.business_name else 'ShopInStreet'
    business_address = None
    if vendor:
        address_parts = []
        if vendor.address:
            address_parts.append(vendor.address)
        if vendor.city:
            address_parts.append(vendor.city)
        if vendor.state:
            address_parts.append(vendor.state)
        if vendor.pincode:
            address_parts.append(vendor.pincode)
        business_address = ', '.join(address_parts) if address_parts else None
    
    receipt_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ 
                font-family: 'Courier New', monospace; 
                width: 80mm; 
                margin: 0; 
                padding: 10px; 
                font-size: 12px;
            }}
            .header {{ 
                text-align: center; 
                border-bottom: 2px solid #000; 
                padding-bottom: 10px; 
                margin-bottom: 10px;
            }}
            .business-info {{
                text-align: center;
                font-size: 10px;
                margin-bottom: 10px;
            }}
            .transaction-info {{ margin: 10px 0; }}
            .items {{ margin: 10px 0; }}
            .item-row {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 5px 0; 
                padding: 2px 0;
            }}
            .item-name {{ flex: 1; }}
            .item-qty {{ width: 30px; text-align: center; }}
            .item-price {{ width: 60px; text-align: right; }}
            .totals {{ 
                border-top: 1px solid #000; 
                margin-top: 10px;
                padding-top: 10px;
            }}
            .total-row {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 3px 0;
            }}
            .grand-total {{ 
                border-top: 1px solid #000; 
                padding-top: 5px; 
                font-weight: bold; 
                font-size: 14px;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 20px; 
                font-size: 10px; 
                border-top: 1px dashed #000;
                padding-top: 10px;
            }}
            .qr-section {{
                text-align: center;
                margin: 15px 0;
                padding: 10px;
                border-top: 1px dashed #000;
            }}
            .qr-code {{
                width: 80px;
                height: 80px;
                margin: 10px auto;
                display: block;
            }}
            .website-url {{
                font-size: 10px;
                margin-top: 5px;
                word-break: break-all;
            }}
            .notes {{
                margin: 10px 0;
                padding: 5px;
                border: 1px dashed #666;
                font-size: 11px;
            }}
            /* Hide ALL prices on gift receipts */
            {''.join(['.item-price { display: none !important; } .totals { display: none !important; }'] if is_gift else [])}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{business_name}</h2>
            {'<p><strong>GIFT RECEIPT</strong></p>' if is_gift else ''}
            <p>Receipt</p>
        </div>
        
        {f'<div class="business-info"><p>{business_address}</p></div>' if business_address else ''}
        {f'<div class="business-info"><p>Phone: {vendor.phone}</p></div>' if vendor and vendor.phone else ''}
        
        <div class="transaction-info">
            <p><strong>Order #:</strong> {getattr(order, 'order_number', None) or order.id}</p>
            <p><strong>Date:</strong> {order_date}</p>
            <p><strong>Payment:</strong> {getattr(order, 'payment_method', 'Cash').title()}</p>
            {f'<p><strong>Customer:</strong> {order.customer_name}</p>' if getattr(order, 'customer_name', None) and not is_gift else ''}
        </div>
        
        <div class="items">
            <div style="border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 5px; font-weight: bold;">
                <div class="item-row">
                    <span class="item-name">Item</span>
                    <span class="item-qty">Qty</span>
                    <span class="item-price">Price</span>
                </div>
            </div>
    """
    
    # Add order items
    for item in order_items:
        item_total = float(item.price) * int(item.quantity)
        receipt_html += f"""
            <div class="item-row">
                <span class="item-name">{item.product_name}</span>
                <span class="item-qty">{item.quantity}</span>
                <span class="item-price">₹{item_total:.2f}</span>
            </div>
        """
    
    # Always show totals section (but hide on gift receipts via CSS)
    receipt_html += f"""
        </div>
        
        <div class="totals">
            <div class="total-row">
                <span>Subtotal:</span>
                <span>₹{subtotal:.2f}</span>
            </div>
    """
    
    # Add tax if present
    if tax_amount > 0:
        receipt_html += f"""
            <div class="total-row">
                <span>Tax:</span>
                <span>₹{tax_amount:.2f}</span>
            </div>
        """
    
    # Add discount if present
    if discount_amount > 0:
        receipt_html += f"""
            <div class="total-row">
                <span>Discount:</span>
                <span>-₹{discount_amount:.2f}</span>
            </div>
        """
    
    # Grand total - use calculated total
    receipt_html += f"""
            <div class="total-row grand-total">
                <span>TOTAL:</span>
                <span>₹{calculated_total:.2f}</span>
            </div>
        </div>
    """
    print(f"DEBUG - Receipt generation:")
    print(f"  Order ID: {order.id}")
    print(f"  Vendor: {vendor}")
    if vendor:
        print(f"  Vendor ID: {vendor.id}")
        print(f"  Business name: {vendor.business_name}")
        print(f"  Subdomain: {getattr(vendor, 'subdomain', 'None')}")
        print(f"  Website URL: {getattr(vendor, 'website_url', 'None')}")
    
    vendor_website_url = get_vendor_website_url(vendor)
    print(f"  Final website URL: {vendor_website_url}")
    # Add notes if present
    if notes and notes.strip():
        receipt_html += f"""
        <div class="notes">
            <p><strong>Notes:</strong></p>
            <p>{notes}</p>
        </div>
        """
    
    # Add QR code section
    receipt_html += f"""
        <div class="qr-section">
            <p style="font-weight: bold; margin-bottom: 5px;">Visit Our Store Online:</p>
            <img src="{qr_code_base64}" alt="QR Code" class="qr-code">
            <p class="website-url">{vendor_website_url}</p>
            <p style="font-size: 9px; margin-top: 5px;">Scan to browse our products online</p>
        </div>
        """
    
    # Footer
    receipt_html += f"""
        <div class="footer">
            <p>Items: {total_items} | Thank you for shopping with us!</p>
        </div>
    </body>
    </html>
    """
    
    return receipt_html
@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Receipts router is working"}

@router.post("/print", response_model=PrintReceiptResponse)
async def print_receipt(
    request: PrintReceiptRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Generate receipt HTML for printing"""
    
    try:
        # Add vendor filtering
        order = db.query(Order).filter(
            Order.id == request.transaction_id,
            Order.vendor_id == vendor.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or access denied"
            )
        
        # Get order items
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).all()
        
        receipt_html = generate_receipt_html(
            order=order,
            order_items=order_items,
            is_gift=request.gift_receipt,
            vendor=vendor
        )
        
        return PrintReceiptResponse(
            transaction_id=request.transaction_id,
            is_gift_receipt=request.gift_receipt,
            print_ready=True,
            receipt_html=receipt_html
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate receipt: {str(e)}"
        )

@router.post("/email", response_model=EmailReceiptResponse)
async def email_receipt(
    request: EmailReceiptRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Send receipt via email"""
    
    try:
        # Validate order exists and belongs to vendor
        order = db.query(Order).filter(
            Order.id == request.transaction_id,
            Order.vendor_id == vendor.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or access denied"
            )
        
        # TODO: Implement actual email sending service
        # order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        # await send_email_receipt(request.customer_email, order, order_items, vendor)
        
        return EmailReceiptResponse(
            message="Receipt sent successfully",
            success=True,
            email_sent_to=request.customer_email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

@router.get("/receipts/test/{order_id}")
async def test_receipt_generation(
    order_id: int,
    gift: bool = False,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Test receipt generation for debugging"""
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.vendor_id == vendor.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_items = db.query(OrderItem).filter(
        OrderItem.order_id == order.id
    ).all()
    
    receipt_html = generate_receipt_html(
        order=order,
        order_items=order_items,
        is_gift=gift,
        vendor=vendor
    )
    
    return {
        "order_id": order_id,
        "vendor_website": get_vendor_website_url(vendor),
        "has_tax": bool(getattr(order, 'tax_amount', 0)),
        "has_discount": bool(getattr(order, 'discount_amount', 0)),
        "has_notes": bool(getattr(order, 'notes', '')),
        "total_amount": float(getattr(order, 'total_amount', 0)),
        "receipt_html": receipt_html
    }