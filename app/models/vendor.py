# app/models/vendor.py - FIXED ENTERPRISE VERSION

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
import os
import base64
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from sqlalchemy.sql import func
from datetime import datetime
import re
import logging
# Enterprise-grade encryption imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.warning("Cryptography library not available - banking data will not be encrypted")

class Vendor(Base):
    __tablename__ = "vendor"  # PostgreSQL table name

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, index=True)

    # EXISTING BASIC BUSINESS INFO (Keep these as they are)
    business_name = Column(String, nullable=False)
    business_category = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    country = Column(String, nullable=False)

    # EXISTING CONTACT INFO (Keep these as they are)
    owner_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True, nullable=False)

    # EXISTING AUTH (Keep these as they are)
    password_hash = Column(String, nullable=False)

    # EXISTING VERIFICATION (Keep these as they are)
    verification_type = Column(String, nullable=False)
    verification_number = Column(String, nullable=False)

    # EXISTING OPTIONAL FIELDS (Keep these as they are)
    website_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    business_logo = Column(String, nullable=True)

    # EXISTING STATUS (Keep these as they are)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    template_id = Column(Integer, default=1, nullable=True)
    template_type = Column(String, default="Default", nullable=True)
    
    # 🔧 FIXED: Enhanced Business Information (removed duplicate business_description)
    business_type = Column(String(50), nullable=True, index=True)  # Corporation, Partnership, etc.
    business_description = Column(Text, nullable=True)  # Keep only one declaration
    timezone = Column(String(50), default="America/Toronto", nullable=False)  # Fixed default
    currency = Column(String(3), default="CAD", nullable=False)  # Fixed default for Canada
    business_hours = Column(String, default="9:00 AM - 6:00 PM")
    
    # Tax & Legal Information (indexed for compliance queries)
    gst_number = Column(String(15), nullable=True, index=True)  # India GST
    hst_pst_number = Column(String(20), nullable=True)  # Canada HST/PST
    pan_card = Column(String(10), nullable=True)  # India PAN
    business_registration_number = Column(String(50), nullable=True, index=True)
    tax_exemption_status = Column(Boolean, default=False, nullable=False)
    
    # 🔧 FIXED: Banking Information - ENCRYPTED for enterprise security (removed duplicates)
    bank_name = Column(String(100), nullable=True)  # Keep only one declaration
    account_number_encrypted = Column(Text, nullable=True)  # Encrypted storage
    routing_code_encrypted = Column(Text, nullable=True)    # Encrypted storage
    account_holder_name = Column(String(100), nullable=True)
    
    # Enhanced Contact Information
    alternate_email = Column(String(255), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    
    # Profile Completion & Analytics
    profile_completed = Column(Boolean, default=False, nullable=False, index=True)
    profile_completion_percentage = Column(Integer, default=0, nullable=False)
    
    # Audit Trail for Compliance
    profile_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    profile_updated_by = Column(Integer, nullable=True)  # User ID who made changes
    
    # Enterprise Compliance & Risk Management
    risk_score = Column(Integer, default=0, nullable=False)  # 0-100 risk assessment
    compliance_status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    last_compliance_check = Column(DateTime(timezone=True), nullable=True)

    subdomain = Column(String(50), nullable=True, index=True)
    domain_type = Column(String(20), default='free', nullable=False, index=True)
    website_status = Column(String(20), default='draft', nullable=False, index=True)
    went_live_at = Column(DateTime(timezone=True), nullable=True)
    subdomain_created_at = Column(DateTime(timezone=True), default=func.now())
    readiness_score = Column(Integer, default=0, nullable=False)

    # RELATIONSHIPS
    orders = relationship("Order", back_populates="vendor", lazy="dynamic")

    # Also update these lines (remove the full module path):
    domain_orders = relationship("DomainOrder", back_populates="vendor", cascade="all, delete-orphan")
    domains = relationship("VendorDomain", back_populates="vendor")
    # ENTERPRISE PERFORMANCE INDEXES
    __table_args__ = (
        Index('idx_vendor_business_profile', 'business_type', 'country', 'profile_completed'),
        Index('idx_vendor_tax_compliance', 'gst_number', 'hst_pst_number', 'compliance_status'),
        Index('idx_vendor_risk_analysis', 'risk_score', 'compliance_status', 'is_verified'),
        Index('idx_vendor_performance', 'profile_completion_percentage', 'created_at'),
    )

    def get_template_type(self):
        """Auto-assign template based on business category"""
        if self.business_category == "Food":
            return "Template8"
        elif self.business_category == "Clothing":
            return "Template7"
        else:
            return "Default"

    def assign_template_based_on_category(self):
        """Assign template ID and type based on business category"""
        template_mapping = {
            "Food": {"id": 8, "type": "Template8"},
            "Clothing": {"id": 7, "type": "Template7"}
        }
    
        if self.business_category in template_mapping:
            template_info = template_mapping[self.business_category]
            self.template_id = template_info["id"]
            self.template_type = template_info["type"]
        else:
            # Default template
            self.template_id = 1
            self.template_type = "Default"   
    # ENTERPRISE ENCRYPTION METHODS
    @classmethod
    def _get_encryption_key(cls) -> bytes:
        """
        Enterprise-grade encryption key management
        In production, use AWS KMS, Azure Key Vault, or HashiCorp Vault
        """
        # Get key from environment
        env_key = os.getenv('BANKING_ENCRYPTION_KEY')
        
        if env_key:
            try:
                return base64.urlsafe_b64decode(env_key.encode())
            except Exception as e:
                logging.error(f"Invalid encryption key format: {e}")
        
        # Generate key for development (NOT for production)
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            password = b"dev-banking-encryption-key-change-in-prod"
            salt = b"salt-change-in-production-env"  # In prod, use random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(password))
        
        raise ValueError("No encryption key available and not in development mode")
    
    def encrypt_banking_data(self, data: str) -> Optional[str]:
        """
        Encrypt sensitive banking information with enterprise security
        Returns None if encryption fails or data is empty
        """
        if not data or not data.strip():
            return None
            
        if not ENCRYPTION_AVAILABLE:
            logging.error("Encryption not available - storing data in plain text (SECURITY RISK)")
            return data  # In production, this should raise an exception
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logging.error(f"Banking data encryption failed: {e}")
            return None
    
    def decrypt_banking_data(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt sensitive banking information with error handling
        Returns None if decryption fails or data is empty
        """
        if not encrypted_data or not encrypted_data.strip():
            return None
            
        if not ENCRYPTION_AVAILABLE:
            logging.warning("Encryption not available - returning data as-is")
            return encrypted_data
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logging.error(f"Banking data decryption failed: {e}")
            return None

    # SECURE PROPERTY METHODS
    @property
    def account_number(self) -> Optional[str]:
        """Get decrypted account number safely"""
        if not self.account_number_encrypted:
            return None
        return self.decrypt_banking_data(self.account_number_encrypted)
    
    @account_number.setter
    def account_number(self, value: Optional[str]):
        """Set encrypted account number safely"""
        if value:
            self.account_number_encrypted = self.encrypt_banking_data(value)
        else:
            self.account_number_encrypted = None
    
    @property
    def routing_code(self) -> Optional[str]:
        """Get decrypted routing code safely"""
        if not self.routing_code_encrypted:
            return None
        return self.decrypt_banking_data(self.routing_code_encrypted)
    
    @routing_code.setter
    def routing_code(self, value: Optional[str]):
        """Set encrypted routing code safely"""
        if value:
            self.routing_code_encrypted = self.encrypt_banking_data(value)
        else:
            self.routing_code_encrypted = None

    # ENTERPRISE HELPER METHODS
    def get_masked_account_number(self) -> Optional[str]:
        """Get masked account number for display (enterprise security)"""
        account = self.account_number
        if not account or len(account) < 4:
            return None
        return "****" + account[-4:]
    
    def is_banking_data_encrypted(self) -> bool:
        """Check if banking data is properly encrypted"""
        return (
            ENCRYPTION_AVAILABLE and 
            self.account_number_encrypted is not None and
            self.routing_code_encrypted is not None
        )

    # COMPLIANCE & RISK METHODS
    def calculate_risk_score(self) -> int:
        """Calculate vendor risk score for compliance (0-100)"""
        score = 50  # Base score
        
        # Profile completion reduces risk
        if self.profile_completed:
            score -= 20
        
        # Verification reduces risk
        if self.is_verified:
            score -= 30
        
        # Missing tax info increases risk
        if self.country == "India" and not self.gst_number:
            score += 25
        if self.country == "Canada" and not self.hst_pst_number:
            score += 25
        
        # Banking info reduces risk
        if self.bank_name and self.account_number:
            score -= 15
        
        # Business description shows professionalism
        if self.business_description and len(self.business_description) > 50:
            score -= 10
        
        # Website shows legitimacy
        if self.website_url:
            score -= 5
        
        # Ensure score is between 0-100
        return max(0, min(100, score))
    
    def update_compliance_status(self):
        """Update compliance status based on profile data"""
        self.risk_score = self.calculate_risk_score()
        
        if self.risk_score <= 30 and self.profile_completed:
            self.compliance_status = "approved"
        elif self.risk_score >= 70:
            self.compliance_status = "high_risk"
        else:
            self.compliance_status = "pending"
        
        self.last_compliance_check = datetime.utcnow()

    # PROFILE COMPLETION CALCULATION
    def calculate_profile_completion(self) -> int:
        """Calculate profile completion percentage"""
        total_fields = 20  # Total important fields
        completed_fields = 0
        
        # Required fields (weight: 1 each)
        required_fields = [
            self.business_name, self.owner_name, self.email, self.phone,
            self.address, self.city, self.state, self.country,
            self.business_category
        ]
        completed_fields += sum(1 for field in required_fields if field and str(field).strip())
        
        # Important optional fields (weight: 0.5 each)
        optional_fields = [
            self.business_type, self.business_description, self.website_url,
            self.gst_number, self.hst_pst_number, self.bank_name,
            self.account_number, self.routing_code, self.account_holder_name,
            self.alternate_email, self.alternate_phone
        ]
        completed_fields += sum(0.5 for field in optional_fields if field and str(field).strip())
        
        percentage = int((completed_fields / total_fields) * 100)
        return min(100, percentage)
    
    def update_profile_completion(self):
        """Update profile completion percentage and status"""
        self.profile_completion_percentage = self.calculate_profile_completion()
        self.profile_completed = self.profile_completion_percentage >= 80
        self.profile_updated_at = datetime.utcnow()

    # STRING REPRESENTATION
    def __repr__(self):
        return f"<Vendor(id={self.id}, business_name='{self.business_name}', email='{self.email}')>"
    
    def get_website_url(self):
        """Get full website URL"""
        if self.subdomain:
            protocol = "https"  # Always use HTTPS in production
            return f"{protocol}://{self.subdomain}.shopinstreet.com"
        return None
    
    def get_website_status_display(self):
        """Get human-readable website status"""
        status_map = {
            'draft': 'Coming Soon',
            'preview': 'Preview Mode',
            'live': 'Live Website'
        }
        return status_map.get(self.website_status, 'Unknown')
    
    def get_domain_type_display(self):
        """Get human-readable domain type"""
        type_map = {
            'free': '🆓 Free Subdomain',
            'purchased': '💼 Professional Domain', 
            'custom': '⭐ Custom Domain'
        }
        return type_map.get(self.domain_type, 'Unknown')
    
    def calculate_readiness_score(self):
        """Calculate website readiness score (0-100)"""
        score = 0
        
        # Basic business info (30 points)
        if self.business_name: score += 5
        if hasattr(self, 'business_description') and self.business_description: score += 10
        if self.business_logo: score += 10
        if hasattr(self, 'business_hours') and self.business_hours: score += 5
        
        # Contact & verification (25 points)
        if self.email: score += 5
        if self.phone: score += 5
        if self.is_verified: score += 15
        
        # Address info (15 points)
        if self.address: score += 5
        if self.city: score += 5
        if self.state: score += 5
        
        # Additional info (30 points)
        if self.website_url: score += 5
        if self.linkedin_url: score += 5
        
        # Check if vendor has products (through relationship)
        try:
            if hasattr(self, 'products') and self.products:
                product_count = len(self.products)
                if product_count >= 1: score += 5
                if product_count >= 3: score += 10
                if product_count >= 5: score += 5
        except:
            pass  # Handle case where products relationship doesn't exist yet
        
        # Update the score in database
        self.readiness_score = score
        return score
    
    def can_go_live(self):
        """Check if vendor can go live (minimum requirements)"""
        current_score = self.calculate_readiness_score()
        
        # Minimum requirements for going live
        has_basic_info = bool(self.business_name and self.email and self.phone)
        has_minimum_score = current_score >= 40
        has_subdomain = bool(self.subdomain)
        
        return has_basic_info and has_minimum_score and has_subdomain
    
    def go_live(self):
        """Make vendor website live"""
        if not self.can_go_live():
            missing_requirements = []
            
            if not self.business_name:
                missing_requirements.append("Business name")
            if not self.email:
                missing_requirements.append("Email address")
            if not self.phone:
                missing_requirements.append("Phone number")
            if self.readiness_score < 40:
                missing_requirements.append("Minimum 40% profile completion")
            if not self.subdomain:
                missing_requirements.append("Subdomain setup")
            
            return {
                "success": False,
                "message": "Cannot go live yet",
                "missing_requirements": missing_requirements,
                "current_score": self.readiness_score,
                "required_score": 40
            }
        
        # Make website live
        self.website_status = 'live'
        self.went_live_at = datetime.utcnow()
        
        return {
            "success": True,
            "message": f"🎉 Your website is now live!",
            "website_url": self.get_website_url(),
            "went_live_at": self.went_live_at.isoformat()
        }
    
    def get_next_steps(self):
        """Get recommended next steps for vendor"""
        steps = []
        current_score = self.calculate_readiness_score()
        
        # Basic profile completion
        if not self.business_logo:
            steps.append("Upload your business logo")
        
        if hasattr(self, 'business_description') and not self.business_description:
            steps.append("Add a business description")
        
        if not self.website_url:
            steps.append("Add your website URL (optional)")
        
        # Product/content steps
        try:
            if hasattr(self, 'products'):
                product_count = len(self.products) if self.products else 0
                if product_count == 0:
                    steps.append("Add your first product/service")
                elif product_count < 3:
                    steps.append("Add more products (recommended: at least 3)")
        except:
            steps.append("Add products/services to your catalog")
        
        # Verification steps
        if not self.is_verified:
            steps.append("Complete business verification")
        
        # Go live step
        if self.can_go_live() and self.website_status != 'live':
            steps.append("🚀 Ready to go live! Launch your website")
        elif current_score < 40:
            steps.append(f"Complete profile to {40 - current_score}% more to go live")
        
        return steps
    
    def get_dashboard_summary(self):
        """Get summary info for vendor dashboard"""
        current_score = self.calculate_readiness_score()
        
        return {
            "website_url": self.get_website_url(),
            "website_status": self.get_website_status_display(),
            "domain_type": self.get_domain_type_display(),
            "readiness_score": current_score,
            "can_go_live": self.can_go_live(),
            "next_steps": self.get_next_steps(),
            "went_live_at": self.went_live_at.isoformat() if self.went_live_at else None,
            "total_products": len(self.products) if hasattr(self, 'products') and self.products else 0
        }
    
    def update_subdomain_if_needed(self, db_session):
        """Update subdomain if business name changed"""
        if not self.subdomain:
            # Generate subdomain if doesn't exist
            new_subdomain = self._generate_subdomain_from_business_name(db_session)
            self.subdomain = new_subdomain
            self.subdomain_created_at = datetime.utcnow()
            return new_subdomain
        return self.subdomain
    
    def _generate_subdomain_from_business_name(self, db_session):
        """Generate subdomain from business name (for existing vendors)"""
        if not self.business_name:
            return f"vendor{self.id}"
        
        # Clean business name
        base = re.sub(r'[^a-zA-Z0-9]', '', self.business_name.lower())
        
        # Remove common words if too long
        if len(base) > 15:
            common_words = ['restaurant', 'food', 'cafe', 'store', 'shop', 'electronics']
            for word in common_words:
                base = base.replace(word, '')
        
        base = base[:15]
        if not base:
            base = f"business{self.id}"
        
        # Check for conflicts and resolve
        subdomain = base
        counter = 1
        
        while True:
            # Check if subdomain exists
            existing = db_session.query(Vendor).filter(
                Vendor.subdomain == subdomain,
                Vendor.id != self.id  # Exclude current vendor
            ).first()
            
            if not existing:
                return subdomain
            
            # Try with city first
            if counter == 1 and self.city:
                city_abbr = self._get_city_abbreviation()
                subdomain = f"{base}{city_abbr}"
                counter += 1
                continue
            
            # Try numbered versions
            subdomain = f"{base}{counter}"
            counter += 1
            
            # Safety break
            if counter > 100:
                import uuid
                return f"{base}{uuid.uuid4().hex[:6]}"
    
    def _get_city_abbreviation(self):
        """Get city abbreviation for subdomain"""
        if not self.city:
            return ""
        
        city_mappings = {
            'bangalore': 'blr', 'bengaluru': 'blr',
            'mumbai': 'mum', 'bombay': 'mum',
            'delhi': 'del', 'new delhi': 'del',
            'hyderabad': 'hyd',
            'chennai': 'che', 'madras': 'che',
            'kolkata': 'kol', 'calcutta': 'kol',
            'pune': 'pune', 'ahmedabad': 'amd'
        }
        
        return city_mappings.get(self.city.lower().strip(), self.city.lower()[:3])
