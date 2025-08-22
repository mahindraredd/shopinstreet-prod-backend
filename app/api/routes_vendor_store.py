# Update your existing routes_vendor_store.py

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.models.vendor import Vendor
from app.models.product import Product
from app.schemas.vendorstore import VendorStoreSchema, TemplateUpdateSchema, VendorStoreSchemaNormal
from app.db.deps import get_db
from app.services.image_service import generate_presigned_url, process_and_upload_images, process_and_upload_images1

# Import the production deployment service
from app.services.template_deployment_service import ProductionTemplateDeployment

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

# 🚀 UPDATED: Production React Template Deployment
@router.put("/vendor/{vendor_id}/template")
def update_vendor_template(
    vendor_id: int, 
    data: TemplateUpdateSchema, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Store previous template for comparison
    previous_template_id = vendor.template_id
    
    # Store original values to prevent auto-override
    original_template_id = data.template_id
    original_template_type = data.template_type if hasattr(data, 'template_type') else f"Template{data.template_id}"
    
    vendor.template_id = original_template_id
    vendor.template_type = original_template_type
    
    print(f"🎨 PRODUCTION UPDATE: Vendor {vendor_id} template: {previous_template_id} → {data.template_id}")
    
    db.commit()
    
    # Verify the assignment stuck
    db.refresh(vendor)
    if vendor.template_id != original_template_id:
        # Force the assignment again if it was overridden
        vendor.template_id = original_template_id
        vendor.template_type = original_template_type
        db.commit()
        db.refresh(vendor)
    
    # 🚀 PRODUCTION: Deploy React template to subdomain if vendor has one
    if vendor.subdomain:
        print(f"🚀 PRODUCTION DEPLOY: Starting Template {original_template_id} deployment to {vendor.subdomain}")
        
        background_tasks.add_task(
            deploy_production_template,
            vendor_id,
            original_template_id,
            vendor.subdomain
        )
        
        deployment_message = f"Production React Template {original_template_id} is building and deploying to {vendor.subdomain}.shopinstreet.com"
        estimated_time = "2-3 minutes"
    else:
        deployment_message = "Template updated (no subdomain assigned)"
        estimated_time = "N/A"
    
    print(f"✅ PRODUCTION: Vendor {vendor_id} template updated to {vendor.template_id}")
    
    return {
        "message": "Template updated successfully", 
        "template_id": vendor.template_id,
        "template_type": vendor.template_type,
        "previous_template_id": previous_template_id,
        "subdomain": vendor.subdomain,
        "website_url": f"https://{vendor.subdomain}.shopinstreet.com" if vendor.subdomain else None,
        "deployment_status": deployment_message,
        "deployment_type": "production_react_app",
        "estimated_time": estimated_time,
        "build_includes": [
            "Full React application",
            "Vendor-specific configuration", 
            "Product integration",
            "Optimized production build",
            "Mobile responsive design"
        ]
    }

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

# 🚀 NEW: Production deployment status endpoint
@router.get("/vendor/{vendor_id}/deployment-status")
def get_deployment_status(vendor_id: int, db: Session = Depends(get_db)):
    """Check production template deployment status"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if not vendor.subdomain:
        return {
            "success": False,
            "error": "No subdomain assigned to vendor",
            "has_subdomain": False
        }
    
    # Check if React app is deployed
    from pathlib import Path
    deployment_path = Path(f"static_sites/{vendor.subdomain}")
    index_path = deployment_path / "index.html"
    assets_path = deployment_path / "assets"
    
    if deployment_path.exists() and index_path.exists():
        import time
        file_age = time.time() - index_path.stat().st_mtime
        
        # Check if it's a React build (has assets folder)
        is_react_build = assets_path.exists()
        
        status = "deployed"
        if file_age < 300:  # Less than 5 minutes
            status = "recently_deployed"
        
        # Count assets for verification
        asset_count = len(list(assets_path.glob("*"))) if assets_path.exists() else 0
        
        return {
            "success": True,
            "status": status,
            "deployment_type": "production_react_app" if is_react_build else "basic_template",
            "template_id": vendor.template_id,
            "template_type": vendor.template_type,
            "subdomain": vendor.subdomain,
            "website_url": f"https://{vendor.subdomain}.shopinstreet.com",
            "last_updated": index_path.stat().st_mtime,
            "deployment_age_minutes": round(file_age / 60, 1),
            "has_subdomain": True,
            "react_assets_count": asset_count,
            "is_production_build": is_react_build
        }
    else:
        return {
            "success": True,
            "status": "not_deployed",
            "message": "Production React template not yet deployed to subdomain",
            "subdomain": vendor.subdomain,
            "has_subdomain": True,
            "deployment_type": "none"
        }

def deploy_production_template(vendor_id: int, template_id: int, subdomain: str):
    """Background task for production React template deployment"""
    
    print(f"🚀 PRODUCTION DEPLOYMENT STARTED")
    print(f"   Vendor: {vendor_id}")
    print(f"   Template: {template_id}")
    print(f"   Subdomain: {subdomain}")
    print(f"   Target: {subdomain}.shopinstreet.com")
    
    try:
        deployment_service = ProductionTemplateDeployment()
        result = deployment_service.deploy_template_to_subdomain(vendor_id, template_id, subdomain)
        
        if result["success"]:
            print(f"✅ PRODUCTION DEPLOYMENT SUCCESS!")
            print(f"   Message: {result['message']}")
            print(f"   Build Time: {result.get('build_time', 'N/A')}")
            print(f"   Files Deployed: {result.get('files_deployed', 'N/A')}")
            print(f"   🌐 LIVE AT: {result['website_url']}")
        else:
            print(f"❌ PRODUCTION DEPLOYMENT FAILED!")
            print(f"   Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ PRODUCTION DEPLOYMENT EXCEPTION: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

# 🚀 NEW: Manual deployment trigger (for testing)
@router.post("/vendor/{vendor_id}/deploy-template")
def manually_deploy_template(
    vendor_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger template deployment (for testing)"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if not vendor.subdomain:
        raise HTTPException(status_code=400, detail="No subdomain assigned")
    
    if not vendor.template_id:
        raise HTTPException(status_code=400, detail="No template selected")
    
    background_tasks.add_task(
        deploy_production_template,
        vendor_id,
        vendor.template_id,
        vendor.subdomain
    )
    
    return {
        "message": "Manual deployment triggered",
        "vendor_id": vendor_id,
        "template_id": vendor.template_id,
        "subdomain": vendor.subdomain,
        "estimated_time": "2-3 minutes"
    }