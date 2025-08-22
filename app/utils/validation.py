# app/utils/validation.py
import re
from typing import Optional

def validate_subdomain(subdomain: str) -> bool:
    """Validate subdomain format and security"""
    
    if not subdomain or not isinstance(subdomain, str):
        return False
    
    # Length check (3-20 characters)
    if len(subdomain) < 3 or len(subdomain) > 20:
        return False
    
    # Format check: alphanumeric and hyphens only
    if not re.match(r'^[a-zA-Z0-9-]+$', subdomain):
        return False
    
    # Cannot start or end with hyphen
    if subdomain.startswith('-') or subdomain.endswith('-'):
        return False
    
    # Reserved subdomains
    reserved = {
        'www', 'api', 'admin', 'mail', 'ftp', 'blog', 'shop',
        'support', 'help', 'status', 'cdn', 'assets', 'static'
    }
    
    if subdomain.lower() in reserved:
        return False
    
    return True

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    
    if not filename:
        return ""
    
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\|?*]', '', filename)
    sanitized = sanitized.replace('..', '')
    
    return sanitized[:255]  # Limit length

def validate_template_id(template_id: int) -> bool:
    """Validate template ID range"""
    
    if not isinstance(template_id, int):
        return False
    
    return 1 <= template_id <= 10  # Adjust range as needed
