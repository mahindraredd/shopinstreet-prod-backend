from sqlalchemy.orm import Session
from app.models.vendor import Vendor

# ✅ Check if vendor exists
def get_vendor_by_email_or_phone(db: Session, email: str, phone: str):
    return db.query(Vendor).filter((Vendor.email == email) | (Vendor.phone == phone)).first()

# ✅ Create vendor - FIXED with template assignment
def create_vendor(db: Session, vendor: Vendor):
    # 🔧 FIX: Assign template based on business category BEFORE saving
    vendor.assign_template_based_on_category()
    
    # Optional: Update other calculated fields
    vendor.update_profile_completion()
    vendor.update_compliance_status()
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor

# ✅ Get vendor by email
def get_vendor_by_email(db: Session, email: str):
    return db.query(Vendor).filter(Vendor.email == email).first()

def get_vendor_by_id(db: Session, vendor_id: int):
    return db.query(Vendor).filter(Vendor.id == vendor_id).first()

# 🆕 UPDATE: Also fix vendor updates to reassign template if category changes
def update_vendor(db: Session, vendor_id: int, vendor_data: dict):
    """Update vendor and reassign template if business_category changed"""
    vendor = get_vendor_by_id(db, vendor_id)
    if not vendor:
        return None
    
    # Store old category to check if it changed
    old_category = vendor.business_category
    
    # Update vendor fields
    for field, value in vendor_data.items():
        if hasattr(vendor, field):
            setattr(vendor, field, value)
    
    # 🔧 FIX: Reassign template if business category changed
    if 'business_category' in vendor_data and vendor.business_category != old_category:
        vendor.assign_template_based_on_category()
    
    # Update other calculated fields
    vendor.update_profile_completion()
    vendor.update_compliance_status()
    
    db.commit()
    db.refresh(vendor)
    return vendor

# 🆕 BULK FIX: Fix existing vendors with wrong templates
def fix_existing_vendor_templates(db: Session):
    """One-time function to fix existing vendors with wrong templates"""
    vendors = db.query(Vendor).all()
    fixed_count = 0
    
    for vendor in vendors:
        old_template_id = vendor.template_id
        old_template_type = vendor.template_type
        
        # Reassign template based on current business category
        vendor.assign_template_based_on_category()
        
        # Check if anything changed
        if (vendor.template_id != old_template_id or 
            vendor.template_type != old_template_type):
            print(f"Fixed vendor {vendor.id}: {vendor.business_name}")
            print(f"  Category: {vendor.business_category}")
            print(f"  Template: {old_template_id}/{old_template_type} → {vendor.template_id}/{vendor.template_type}")
            fixed_count += 1
    
    if fixed_count > 0:
        db.commit()
        print(f"✅ Fixed {fixed_count} vendors")
    else:
        print("✅ All vendors already have correct templates")
    
    return fixed_count

# 🆕 DEBUG: Function to check template assignments
def debug_vendor_templates(db: Session, limit: int = 10):
    """Debug function to check template assignments"""
    vendors = db.query(Vendor).limit(limit).all()
    
    print(f"\n=== VENDOR TEMPLATE DEBUG (showing {len(vendors)} vendors) ===")
    for vendor in vendors:
        expected_template_id = 7 if vendor.business_category == "Food" else (8 if vendor.business_category == "Clothing" else 1)
        expected_template_type = "Template7" if vendor.business_category == "Food" else ("Template8" if vendor.business_category == "Clothing" else "Default")
        
        status = "✅" if (vendor.template_id == expected_template_id and vendor.template_type == expected_template_type) else "❌"
        
        print(f"{status} ID:{vendor.id} | {vendor.business_name[:20]:20} | Category:{vendor.business_category:10} | Template:{vendor.template_id}/{vendor.template_type:10} | Expected:{expected_template_id}/{expected_template_type}")

# 🆕 ALTERNATIVE: Use SQLAlchemy events for automatic assignment (Optional)
from sqlalchemy import event

from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.vendor import Vendor

@event.listens_for(Vendor, 'before_insert')
def auto_assign_template_on_insert(mapper, connection, target):
    """Automatically assign template when creating new vendor"""
    target.assign_template_based_on_category()

@event.listens_for(Vendor, 'before_update')  
def auto_assign_template_on_update(mapper, connection, target):
    """Only update template if business_category actually changed"""
    # Check if business_category changed
    if hasattr(target, '_sa_instance_state'):
        history = target._sa_instance_state.attrs.business_category.history
        if history.has_changes():
            # Only auto-assign if business category changed
            target.assign_template_based_on_category()
    # If business_category didn't change, don't touch the template