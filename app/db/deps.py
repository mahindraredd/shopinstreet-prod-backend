from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.vendor import Vendor
import traceback

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/vendor/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_vendor(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Vendor:
    print(f"🔍 DEBUG: Received token: {token[:20]}..." if token else "❌ No token received")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        print(f"🔑 DEBUG: SECRET_KEY exists: {bool(settings.SECRET_KEY)}")
        print(f"🔑 DEBUG: ALGORITHM: {settings.ALGORITHM}")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"✅ DEBUG: JWT decoded successfully: {payload}")
        
        email: str = payload.get("sub")
        if email is None:
            print("❌ DEBUG: No 'sub' field in JWT payload")
            raise credentials_exception
        
        print(f"📧 DEBUG: Extracted email: {email}")
        
    except JWTError as e:
        print(f"❌ DEBUG: JWT Error: {str(e)}")
        print(f"❌ DEBUG: JWT Error traceback: {traceback.format_exc()}")
        raise credentials_exception
    except Exception as e:
        print(f"💥 DEBUG: Unexpected error in token validation: {str(e)}")
        print(f"💥 DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error during authentication: {str(e)}")

    try:
        print(f"🔍 DEBUG: Querying vendor with email: {email}")
        vendor = db.query(Vendor).filter(Vendor.email == email).first()
        
        if vendor is None:
            print(f"❌ DEBUG: No vendor found with email: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Vendor not found"
            )
        
        print(f"✅ DEBUG: Vendor found: {vendor.id} - {vendor.email}")
        return vendor
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"💥 DEBUG: Database error when fetching vendor: {str(e)}")
        print(f"💥 DEBUG: Database error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")