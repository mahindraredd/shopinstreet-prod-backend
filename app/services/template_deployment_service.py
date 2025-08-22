# app/services/template_deployment_service.py
import subprocess
import shutil
import os
import json
from pathlib import Path
from typing import Dict, Any
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from requests import Session

from app.db.deps import get_db
from app.models.vendor import Vendor
from app.schemas.vendorstore import TemplateUpdateSchema
router = APIRouter()
class ProductionTemplateDeployment:
    """
    Production-grade template deployment service
    Builds React apps and deploys to subdomains
    """
    
    def __init__(self):
        # Your exact paths
        self.frontend_project_path = Path("C:/Users/rajas/ShopInstreet_vendorside_frontend/shopinstreet_frontend_vendorside")
        self.templates_path = self.frontend_project_path / "src/components/storeTemplates"
        self.deployment_base = Path("static_sites")
        
    def deploy_template_to_subdomain(self, vendor_id: int, template_id: int, subdomain: str) -> Dict[str, Any]:
        """
        Deploy a React template to vendor's subdomain
        """
        try:
            print(f"🚀 PRODUCTION DEPLOY: Template {template_id} to {subdomain}")
            
            # Get vendor data
            vendor_data = self._get_vendor_data(vendor_id)
            if not vendor_data:
                return {"success": False, "error": "Vendor not found"}
            
            # Create vendor-specific build
            build_result = self._build_vendor_template(vendor_data, template_id)
            if not build_result["success"]:
                return build_result
            
            # Deploy to subdomain
            deploy_result = self._deploy_to_subdomain(build_result["build_path"], subdomain)
            
            # Cleanup temporary build
            self._cleanup_temp_build(build_result["build_path"])
            
            if deploy_result["success"]:
                return {
                    "success": True,
                    "message": f"Template {template_id} deployed to {subdomain}",
                    "website_url": f"https://{subdomain}.shopinstreet.com",
                    "template_id": template_id,
                    "build_time": build_result.get("build_time"),
                    "files_deployed": deploy_result.get("files_count")
                }
            else:
                return deploy_result
                
        except Exception as e:
            print(f"❌ DEPLOYMENT ERROR: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_vendor_data(self, vendor_id: int) -> Dict[str, Any]:
        """Get vendor and product data"""
        try:
            from app.db.session import SessionLocal
            from app.models.vendor import Vendor
            from app.models.product import Product
            
            db = SessionLocal()
            try:
                vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
                if not vendor:
                    return None
                
                products = db.query(Product).filter(Product.vendor_id == vendor_id).all()
                
                return {
                    "vendor_id": vendor_id,
                    "business_name": vendor.business_name,
                    "business_category": vendor.business_category,
                    "owner_name": vendor.owner_name,
                    "email": vendor.email,
                    "phone": vendor.phone,
                    "address": vendor.address,
                    "city": vendor.city,
                    "state": vendor.state,
                    "pincode": vendor.pincode,
                    "country": vendor.country,
                    "subdomain": vendor.subdomain,
                    "website_url": vendor.website_url,
                    "business_logo": vendor.business_logo,
                    "products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "description": p.description,
                            "price": float(p.price),
                            "category": p.category,
                            "image_urls": p.image_urls if hasattr(p, 'image_urls') else []
                        } for p in products
                    ]
                }
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error getting vendor data: {e}")
            return None
    
    def _build_vendor_template(self, vendor_data: Dict[str, Any], template_id: int) -> Dict[str, Any]:
        """
        Build React app with vendor-specific configuration
        """
        import time
        start_time = time.time()
        
        try:
            # Create temporary build directory
            temp_dir = tempfile.mkdtemp(prefix=f"build_{vendor_data['vendor_id']}_")
            temp_path = Path(temp_dir)
            
            print(f"📦 Building in: {temp_path}")
            
            # Copy frontend project to temp directory
            shutil.copytree(self.frontend_project_path, temp_path / "build", 
                          ignore=shutil.ignore_patterns('node_modules', 'dist', '.git'))
            
            build_path = temp_path / "build"
            
            # Create vendor-specific configuration
            self._create_vendor_config(build_path, vendor_data, template_id)
            
            # Update index.html to load specific template
            self._update_index_html(build_path, template_id)
            
            # Install dependencies if needed
            if not (build_path / "node_modules").exists():
                print("📥 Installing dependencies...")
                result = subprocess.run(
                    ["npm", "install"], 
                    cwd=build_path, 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    return {"success": False, "error": f"npm install failed: {result.stderr}"}
            
            # Build the React app
            print("🔨 Building React app...")
            result = subprocess.run(
                ["npm", "run", "build"], 
                cwd=build_path, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Build failed: {result.stderr}"}
            
            build_time = time.time() - start_time
            
            return {
                "success": True,
                "build_path": build_path / "dist",  # Vite builds to 'dist'
                "build_time": f"{build_time:.2f}s"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Build error: {str(e)}"}
    
    def _create_vendor_config(self, build_path: Path, vendor_data: Dict[str, Any], template_id: int):
        """Create vendor-specific configuration files"""
        
        # Create config file for the React app
        config = {
            "vendor": vendor_data,
            "template_id": template_id,
            "api_base_url": "https://api.shopinstreet.com",  # Your production API URL
            "mode": "subdomain_production"
        }
        
        # Save as JSON that React can import
        config_path = build_path / "src" / "vendor-config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📄 Created vendor config: {config_path}")
    
    def _update_index_html(self, build_path: Path, template_id: int):
        """Update index.html to load specific template"""
        
        index_path = build_path / "index.html"
        if index_path.exists():
            content = index_path.read_text()
            
            # Add template-specific meta tags
            meta_tags = f"""
    <meta name="template-id" content="{template_id}">
    <meta name="app-mode" content="subdomain">
    <script>window.TEMPLATE_ID = {template_id};</script>
            """
            
            # Insert before closing head tag
            content = content.replace("</head>", f"{meta_tags}\n</head>")
            index_path.write_text(content)
    
    def _deploy_to_subdomain(self, build_dist_path: Path, subdomain: str) -> Dict[str, Any]:
        """Deploy built React app to subdomain directory"""
        
        try:
            deployment_path = self.deployment_base / subdomain
            
            # Remove existing deployment
            if deployment_path.exists():
                shutil.rmtree(deployment_path)
            
            # Copy built files
            shutil.copytree(build_dist_path, deployment_path)
            
            # Count deployed files
            file_count = len(list(deployment_path.rglob("*")))
            
            print(f"🚀 Deployed {file_count} files to: {deployment_path}")
            
            return {
                "success": True,
                "deployment_path": str(deployment_path),
                "files_count": file_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Deployment error: {str(e)}"}
    
    def _cleanup_temp_build(self, build_path: Path):
        """Clean up temporary build directory"""
        try:
            if build_path.exists():
                shutil.rmtree(build_path.parent)
                print(f"🧹 Cleaned up temp build")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


# Updated routes_vendor_store.py - Enhanced template update
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
    
    previous_template_id = vendor.template_id
    
    # Update template in database
    vendor.template_id = data.template_id
    vendor.template_type = data.template_type if hasattr(data, 'template_type') else f"Template{data.template_id}"
    
    db.commit()
    db.refresh(vendor)
    
    print(f"🎨 Template updated: {previous_template_id} → {data.template_id} for {vendor.business_name}")
    
    # Deploy production React template to subdomain
    if vendor.subdomain:
        background_tasks.add_task(
            deploy_production_template,
            vendor_id,
            data.template_id,
            vendor.subdomain
        )
        deployment_message = f"Production React Template {data.template_id} building and deploying..."
    else:
        deployment_message = "Template updated (no subdomain assigned)"
    
    return {
        "message": "Template updated successfully", 
        "template_id": vendor.template_id,
        "template_type": vendor.template_type,
        "previous_template_id": previous_template_id,
        "subdomain": vendor.subdomain,
        "website_url": f"https://{vendor.subdomain}.shopinstreet.com" if vendor.subdomain else None,
        "deployment_status": deployment_message,
        "deployment_time": "~2-3 minutes (production build)",
        "deployment_type": "full_react_app"
    }

def deploy_production_template(vendor_id: int, template_id: int, subdomain: str):
    """Background task for production template deployment"""
    
    print(f"🚀 PRODUCTION DEPLOYMENT STARTED: Vendor {vendor_id}, Template {template_id}")
    
    try:
        deployment_service = ProductionTemplateDeployment()
        result = deployment_service.deploy_template_to_subdomain(vendor_id, template_id, subdomain)
        
        if result["success"]:
            print(f"✅ PRODUCTION DEPLOYMENT SUCCESS: {result['message']}")
            print(f"🌐 Live at: {result['website_url']}")
        else:
            print(f"❌ PRODUCTION DEPLOYMENT FAILED: {result['error']}")
            
    except Exception as e:
        print(f"❌ PRODUCTION DEPLOYMENT ERROR: {e}")

# Health check endpoint
@router.get("/vendor/{vendor_id}/template-deployment-status")
def get_template_deployment_status(vendor_id: int, db: Session = Depends(get_db)):
    """Check if template is deployed and working"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if not vendor.subdomain:
        return {"deployed": False, "reason": "No subdomain assigned"}
    
    deployment_path = Path(f"static_sites/{vendor.subdomain}")
    
    if not deployment_path.exists():
        return {"deployed": False, "reason": "No deployment found"}
    
    # Check for React app files
    required_files = ["index.html", "assets"]
    
    status = {
        "deployed": True,
        "subdomain": vendor.subdomain,
        "template_id": vendor.template_id,
        "website_url": f"https://{vendor.subdomain}.shopinstreet.com",
        "deployment_path": str(deployment_path),
        "files_check": {}
    }
    
    for file_name in required_files:
        file_path = deployment_path / file_name
        status["files_check"][file_name] = file_path.exists()
    
    # Check if it's a recent deployment
    index_path = deployment_path / "index.html"
    if index_path.exists():
        import time
        file_age = time.time() - index_path.stat().st_mtime
        status["last_deployed"] = f"{file_age/60:.1f} minutes ago"
        status["recent_deployment"] = file_age < 300  # Less than 5 minutes
    
    return status