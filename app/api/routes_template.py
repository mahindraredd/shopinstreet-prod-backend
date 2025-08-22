# app/api/routes_template.py
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.services.template_service import TemplateService
from app.schemas.template import TemplateResponse, TemplateSelectionRequest

router = APIRouter()
template_service = TemplateService()

@router.get("/templates", response_model=List[TemplateResponse])
async def get_available_templates(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get all available templates"""
    try:
        templates = template_service.get_available_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@router.post("/select-template")
async def select_template(
    template_data: TemplateSelectionRequest,
    background_tasks: BackgroundTasks,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Select and deploy template to vendor's subdomain"""
    try:
        # Validate template ID
        if template_data.template_id < 1 or template_data.template_id > 4:
            raise HTTPException(status_code=400, detail="Invalid template ID")
        
        # Ensure vendor has subdomain
        if not vendor.subdomain:
            raise HTTPException(status_code=400, detail="No subdomain assigned to vendor")
        
        # Update vendor's template selection
        vendor.template_id = template_data.template_id
        vendor.template_type = f"Template{template_data.template_id}"
        db.commit()
        
        # Deploy template in background
        background_tasks.add_task(
            deploy_template_background,
            vendor.id,
            template_data.template_id
        )
        
        return {
            "success": True,
            "message": "Template selected successfully",
            "template_id": template_data.template_id,
            "subdomain": vendor.subdomain,
            "website_url": f"https://{vendor.subdomain}.shopinstreet.com",
            "deployment_status": "in_progress"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template selection failed: {str(e)}")

@router.get("/my-website")
async def get_my_website_info(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get vendor's current website information"""
    try:
        website_info = {
            "subdomain": vendor.subdomain,
            "website_url": f"https://{vendor.subdomain}.shopinstreet.com" if vendor.subdomain else None,
            "template_id": vendor.template_id,
            "template_type": vendor.template_type,
            "website_status": vendor.website_status,
            "domain_type": vendor.domain_type,
            "went_live_at": vendor.went_live_at.isoformat() if vendor.went_live_at else None,
            "readiness_score": vendor.readiness_score,
            "can_go_live": vendor.can_go_live(),
            "next_steps": vendor.get_next_steps()
        }
        
        return {
            "success": True,
            "website_info": website_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get website info: {str(e)}")

@router.post("/go-live")
async def make_website_live(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Make vendor's website live"""
    try:
        result = vendor.go_live()
        
        if result["success"]:
            db.commit()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make website live: {str(e)}")

@router.get("/preview/{template_id}")
async def preview_template(
    template_id: int,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Preview a template with vendor's data"""
    try:
        if template_id < 1 or template_id > 4:
            raise HTTPException(status_code=400, detail="Invalid template ID")
        
        # Generate preview HTML with vendor data
        preview_html = generate_template_preview(template_id, vendor)
        
        return HTMLResponse(content=preview_html)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

def generate_template_preview(template_id: int, vendor: Vendor) -> str:
    """Generate template preview HTML"""
    
    # Template-specific preview content
    templates = {
        1: {
            "name": "Modern Business",
            "color_scheme": "#2563eb",
            "style": "professional"
        },
        2: {
            "name": "E-commerce Store",
            "color_scheme": "#059669", 
            "style": "ecommerce"
        },
        3: {
            "name": "Restaurant & Food",
            "color_scheme": "#dc2626",
            "style": "restaurant"
        },
        4: {
            "name": "Portfolio Showcase",
            "color_scheme": "#7c3aed",
            "style": "portfolio"
        }
    }
    
    template_info = templates.get(template_id, templates[1])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vendor.business_name} - {template_info['name']} Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        .preview-banner {{
            background: {template_info['color_scheme']};
            color: white;
            text-align: center;
            padding: 10px;
            position: fixed;
            top: 0;
            width: 100%;
            z-index: 1000;
            font-weight: bold;
        }}
        
        .main-content {{
            margin-top: 50px;
            min-height: 100vh;
            background: linear-gradient(135deg, {template_info['color_scheme']}22 0%, {template_info['color_scheme']}11 100%);
        }}
        
        .hero-section {{
            background: {template_info['color_scheme']};
            color: white;
            text-align: center;
            padding: 4rem 2rem;
        }}
        
        .hero-title {{
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }}
        
        .hero-subtitle {{
            font-size: 1.3rem;
            opacity: 0.9;
            margin-bottom: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .section {{
            background: white;
            margin: 2rem 0;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .section-title {{
            color: {template_info['color_scheme']};
            font-size: 2rem;
            margin-bottom: 1rem;
            border-bottom: 3px solid {template_info['color_scheme']};
            padding-bottom: 0.5rem;
        }}
        
        .contact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}
        
        .contact-card {{
            background: {template_info['color_scheme']};
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
        }}
        
        .contact-icon {{
            font-size: 2rem;
            margin-bottom: 1rem;
        }}
        
        .cta-section {{
            background: {template_info['color_scheme']};
            color: white;
            text-align: center;
            padding: 3rem 2rem;
            border-radius: 10px;
            margin: 2rem 0;
        }}
        
        .cta-button {{
            background: white;
            color: {template_info['color_scheme']};
            padding: 1rem 2rem;
            border: none;
            border-radius: 25px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            margin-top: 1rem;
        }}
        
        @media (max-width: 768px) {{
            .hero-title {{ font-size: 2rem; }}
            .container {{ padding: 1rem; }}
            .contact-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="preview-banner">
        🎨 Template Preview: {template_info['name']} | This is how your website will look
    </div>
    
    <div class="main-content">
        <div class="hero-section">
            <h1 class="hero-title">{vendor.business_name}</h1>
            <p class="hero-subtitle">{vendor.business_category} | {vendor.city}, {vendor.state}</p>
            <p>Welcome to our {template_info['style']} website experience</p>
        </div>
        
        <div class="container">
            <div class="section">
                <h2 class="section-title">About Our Business</h2>
                <p style="font-size: 1.1rem; line-height: 1.8;">
                    {getattr(vendor, 'business_description', None) or f"Welcome to {vendor.business_name}! We are a leading {vendor.business_category.lower()} business located in {vendor.city}, {vendor.state}. Our commitment to excellence and customer satisfaction sets us apart in the industry."}
                </p>
            </div>
            
            <div class="section">
                <h2 class="section-title">Contact Information</h2>
                <div class="contact-grid">
                    <div class="contact-card">
                        <div class="contact-icon">👤</div>
                        <h3>Owner</h3>
                        <p>{vendor.owner_name}</p>
                    </div>
                    <div class="contact-card">
                        <div class="contact-icon">📧</div>
                        <h3>Email</h3>
                        <p>{vendor.email}</p>
                    </div>
                    <div class="contact-card">
                        <div class="contact-icon">📞</div>
                        <h3>Phone</h3>
                        <p>{vendor.phone}</p>
                    </div>
                    <div class="contact-card">
                        <div class="contact-icon">📍</div>
                        <h3>Location</h3>
                        <p>{vendor.city}, {vendor.state}</p>
                    </div>
                </div>
            </div>
            
            <div class="cta-section">
                <h2>Ready to Get Started?</h2>
                <p>Contact us today to learn more about our services and how we can help you.</p>
                <button class="cta-button">Get In Touch</button>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def deploy_template_background(vendor_id: int, template_id: int):
    """Background task to deploy template"""
    try:
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if vendor:
                success = template_service.deploy_template_to_subdomain(vendor, template_id)
                if success:
                    print(f"Template {template_id} deployed successfully for {vendor.subdomain}")
                else:
                    print(f"Failed to deploy template {template_id} for {vendor.subdomain}")
        finally:
            db.close()
    
    except Exception as e:
        print(f"Background template deployment failed: {e}")


