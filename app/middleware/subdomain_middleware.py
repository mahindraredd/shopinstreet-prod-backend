# app/middleware/subdomain_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.vendor import Vendor
from pathlib import Path
import re
import logging
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

class SubdomainMiddleware(BaseHTTPMiddleware):
    """
    Production-ready subdomain middleware with bulletproof error handling
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.reserved_subdomains = {
            'www', 'api', 'admin', 'mail', 'ftp', 'blog', 'shop', 
            'support', 'help', 'status', 'cdn', 'assets'
        }
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatcher with comprehensive error handling"""
        
        try:
            # Extract subdomain safely
            subdomain = self.extract_subdomain(request.headers.get("host", ""))
            request.state.subdomain = subdomain
            
            # Handle subdomain requests
            if subdomain and self.should_handle_subdomain(request, subdomain):
                template_response = await self.serve_subdomain_safely(subdomain, request)
                if template_response:
                    return template_response
            
            # Continue with normal processing
            return await call_next(request)
            
        except Exception as e:
            # Log error but don't expose details to user
            logger.error(f"Subdomain middleware error: {e}")
            
            # Return generic error for subdomain requests
            subdomain = getattr(request.state, 'subdomain', None)
            if subdomain:
                return HTMLResponse(
                    self.get_error_page("Service temporarily unavailable"),
                    status_code=503
                )
            
            # Continue with normal processing for non-subdomain requests
            return await call_next(request)
    
    def extract_subdomain(self, host: str) -> Optional[str]:
        """Safely extract subdomain with validation"""
        
        if not host or "." not in host:
            return None
        
        try:
            parts = host.split(".")
            if len(parts) < 2:
                return None
            
            potential_subdomain = parts[0].lower()
            
            # Validate subdomain format
            if self.validate_subdomain(potential_subdomain):
                return potential_subdomain
                
        except Exception as e:
            logger.warning(f"Subdomain extraction error: {e}")
        
        return None
    
    def validate_subdomain(self, subdomain: str) -> bool:
        """Validate subdomain format and security"""
        
        if not subdomain:
            return False
        
        # Length check
        if len(subdomain) < 3 or len(subdomain) > 20:
            return False
        
        # Format check: alphanumeric and hyphens only
        if not re.match(r'^[a-zA-Z0-9-]+$', subdomain):
            return False
        
        # Cannot start or end with hyphen
        if subdomain.startswith('-') or subdomain.endswith('-'):
            return False
        
        # Reserved subdomain check
        if subdomain in self.reserved_subdomains:
            return False
        
        return True
    
    def should_handle_subdomain(self, request: Request, subdomain: str) -> bool:
        """Determine if we should handle this subdomain request"""
        
        # Skip API requests
        if request.url.path.startswith("/api"):
            return False
        
        # Skip static assets
        if request.url.path.startswith("/static"):
            return False
        
        # Handle root and HTML requests
        if request.url.path in ["/", ""] or request.url.path.endswith(".html"):
            return True
        
        return False
    
    async def serve_subdomain_safely(self, subdomain: str, request: Request) -> Optional[HTMLResponse]:
        """Serve subdomain content with error handling"""
        
        try:
            # Get vendor from database
            vendor = await self.get_vendor_safely(subdomain)
            
            if not vendor:
                return HTMLResponse(
                    self.get_error_page("Website not found", subdomain),
                    status_code=404
                )
            
            # Serve template content
            return await self.serve_template_safely(vendor, request)
            
        except Exception as e:
            logger.error(f"Error serving subdomain {subdomain}: {e}")
            return HTMLResponse(
                self.get_error_page("Service temporarily unavailable"),
                status_code=503
            )
    
    async def get_vendor_safely(self, subdomain: str) -> Optional[Vendor]:
        """Get vendor with database error handling"""
        
        db = None
        try:
            db = SessionLocal()
            vendor = db.query(Vendor).filter(Vendor.subdomain == subdomain).first()
            return vendor
            
        except Exception as e:
            logger.error(f"Database error for subdomain {subdomain}: {e}")
            return None
            
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass
    
    async def serve_template_safely(self, vendor: Vendor, request: Request) -> Optional[HTMLResponse]:
        """Serve template with file system error handling"""
        
        try:
            # Check for deployed template
            template_path = Path(f"static_sites/{vendor.subdomain}")
            index_file = template_path / "index.html"
            
            if index_file.exists() and self.is_safe_path(index_file):
                try:
                    content = index_file.read_text(encoding='utf-8')
                    return HTMLResponse(content=content)
                except Exception as e:
                    logger.warning(f"Error reading template file {index_file}: {e}")
            
            # Generate default template
            return HTMLResponse(content=self.generate_default_template(vendor))
            
        except Exception as e:
            logger.error(f"Template serving error for {vendor.subdomain}: {e}")
            return HTMLResponse(
                content=self.get_error_page("Website temporarily unavailable"),
                status_code=503
            )
    
    def is_safe_path(self, file_path: Path) -> bool:
        """Prevent path traversal attacks"""
        
        try:
            # Resolve the path and check it's within allowed directory
            resolved_path = file_path.resolve()
            allowed_base = Path("static_sites").resolve()
            
            return str(resolved_path).startswith(str(allowed_base))
            
        except Exception:
            return False
    
    def generate_default_template(self, vendor: Vendor) -> str:
        """Generate safe default template"""
        
        # Escape vendor data to prevent XSS
        business_name = self.escape_html(vendor.business_name)
        business_category = self.escape_html(vendor.business_category)
        owner_name = self.escape_html(vendor.owner_name)
        email = self.escape_html(vendor.email)
        phone = self.escape_html(vendor.phone)
        city = self.escape_html(vendor.city)
        state = self.escape_html(vendor.state)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 2rem;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
        .info {{ background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin: 1rem 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{business_name}</h1>
        <p><strong>Category:</strong> {business_category}</p>
        
        <div class="info">
            <h3>Contact Information</h3>
            <p><strong>Owner:</strong> {owner_name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Location:</strong> {city}, {state}</p>
        </div>
        
        <div class="info">
            <h3>🚀 Website Coming Soon!</h3>
            <p>We're building an amazing website experience. Check back soon!</p>
        </div>
    </div>
</body>
</html>"""
    
    def escape_html(self, text: str) -> str:
        """Escape HTML to prevent XSS"""
        
        if not text:
            return ""
        
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))
    
    def get_error_page(self, message: str, subdomain: str = "") -> str:
        """Generate safe error page"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background: #f0f0f0;
        }}
        .error-container {{
            max-width: 500px;
            margin: 0 auto;
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Oops!</h1>
        <p>{self.escape_html(message)}</p>
        {f"<p>Subdomain: {self.escape_html(subdomain)}</p>" if subdomain else ""}
        <p><a href="https://shopinstreet.com">← Back to main site</a></p>
    </div>
</body>
</html>"""
