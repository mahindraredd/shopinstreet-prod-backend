import shutil
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.models.vendor import Vendor

class TemplateService:
    """
    Service to handle template deployment and management
    """
    
    def __init__(self):
        self.templates_dir = Path("templates")
        self.deployed_sites_dir = Path("static_sites")
        
        # Ensure directories exist
        self.templates_dir.mkdir(exist_ok=True)
        self.deployed_sites_dir.mkdir(exist_ok=True)
    
    def deploy_template_to_subdomain(self, vendor: Vendor, template_id: int) -> bool:
        """
        Deploy selected template to vendor's subdomain
        """
        try:
            if not vendor.subdomain:
                return False
            
            template_source = self.templates_dir / f"template{template_id}"
            deployment_target = self.deployed_sites_dir / vendor.subdomain
            
            # Remove existing deployment
            if deployment_target.exists():
                shutil.rmtree(deployment_target)
            
            # Copy template to deployment directory
            if template_source.exists():
                shutil.copytree(template_source, deployment_target)
                
                # Customize template with vendor data
                self.customize_template(deployment_target, vendor)
                
                return True
            else:
                # Template doesn't exist, create basic template
                return self.create_basic_template(deployment_target, vendor)
        
        except Exception as e:
            print(f"Error deploying template: {e}")
            return False
    
    def customize_template(self, template_path: Path, vendor: Vendor):
        """
        Customize template with vendor's business data
        """
        try:
            index_file = template_path / "index.html"
            if index_file.exists():
                content = index_file.read_text(encoding='utf-8')
                
                # Replace placeholders with actual data
                replacements = {
                    '{{BUSINESS_NAME}}': vendor.business_name,
                    '{{OWNER_NAME}}': vendor.owner_name,
                    '{{EMAIL}}': vendor.email,
                    '{{PHONE}}': vendor.phone,
                    '{{ADDRESS}}': vendor.address,
                    '{{CITY}}': vendor.city,
                    '{{STATE}}': vendor.state,
                    '{{PINCODE}}': vendor.pincode,
                    '{{COUNTRY}}': vendor.country,
                    '{{BUSINESS_CATEGORY}}': vendor.business_category,
                    '{{BUSINESS_DESCRIPTION}}': getattr(vendor, 'business_description', '') or f"Welcome to {vendor.business_name}!",
                    '{{WEBSITE_URL}}': vendor.website_url or '',
                }
                
                for placeholder, value in replacements.items():
                    content = content.replace(placeholder, str(value))
                
                index_file.write_text(content, encoding='utf-8')
        
        except Exception as e:
            print(f"Error customizing template: {e}")
    
    def create_basic_template(self, deployment_path: Path, vendor: Vendor) -> bool:
        """
        Create a basic template when specific template doesn't exist
        """
        try:
            deployment_path.mkdir(parents=True, exist_ok=True)
            
            # Create basic index.html
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vendor.business_name}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f4f4f4; 
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 0 10px rgba(0,0,0,0.1); 
        }}
        h1 {{ color: #333; }}
        .contact {{ 
            background: #e9ecef; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 20px 0; 
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{vendor.business_name}</h1>
        <p><strong>Category:</strong> {vendor.business_category}</p>
        <p><strong>Owner:</strong> {vendor.owner_name}</p>
        
        <div class="contact">
            <h3>Contact Information</h3>
            <p><strong>Email:</strong> {vendor.email}</p>
            <p><strong>Phone:</strong> {vendor.phone}</p>
            <p><strong>Address:</strong> {vendor.address}, {vendor.city}, {vendor.state} {vendor.pincode}</p>
        </div>
        
        <p><em>Website template coming soon! We're building something amazing for you.</em></p>
    </div>
</body>
</html>"""
            
            index_file = deployment_path / "index.html"
            index_file.write_text(html_content, encoding='utf-8')
            
            return True
        
        except Exception as e:
            print(f"Error creating basic template: {e}")
            return False
    
    def get_available_templates(self):
        """
        Get list of available templates
        """
        templates = []
        
        for i in range(1, 5):  # Templates 1-4
            template_dir = self.templates_dir / f"template{i}"
            
            template_info = {
                "id": i,
                "name": f"Template {i}",
                "path": str(template_dir),
                "exists": template_dir.exists(),
                "preview_url": f"/api/templates/{i}/preview"
            }
            
            # Add specific template details
            if i == 1:
                template_info.update({
                    "name": "Modern Business",
                    "description": "Clean and professional design perfect for any business",
                    "category": "business"
                })
            elif i == 2:
                template_info.update({
                    "name": "E-commerce Store",
                    "description": "Complete online store with product showcase",
                    "category": "ecommerce"
                })
            elif i == 3:
                template_info.update({
                    "name": "Restaurant & Food",
                    "description": "Perfect for restaurants, cafes, and food businesses",
                    "category": "restaurant"
                })
            elif i == 4:
                template_info.update({
                    "name": "Portfolio Showcase",
                    "description": "Showcase your work and attract clients",
                    "category": "portfolio"
                })
            
            templates.append(template_info)
        
        return templates