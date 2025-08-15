from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.models.models import User
import os

# Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your_secret_key"  # Use env var in prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Security scheme
security = HTTPBearer()

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> int:
    """
    Extract user_id from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        print(f"Decoding token: {credentials.credentials}")
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = str(payload.get("sub"))  # This comes as string
        print(f"Extracted user_id (string): {user_id_str}")
        
        if user_id_str is None:
            print("ERROR: No 'sub' field in token payload")
            raise credentials_exception
            
        # Convert string to integer - THIS WAS MISSING!
        try:
            user_id = int(user_id_str)
            print(f"Converted user_id to int: {user_id}")
        except (ValueError, TypeError) as e:
            print(f"ERROR: Could not convert user_id to int: {user_id_str}, error: {e}")
            raise credentials_exception
            
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            print("ERROR: Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"Unexpected error in token validation: {e}")
        raise credentials_exception
    
    # Optional: Verify user still exists in database
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            print(f"ERROR: User {user_id} not found in database")
            raise credentials_exception
        
        print(f"✓ User {user_id} found in database: {user.email if hasattr(user, 'email') else 'no email field'}")
        
    except Exception as e:
        print(f"Database error while checking user: {e}")
        raise credentials_exception
    
    print(f"✓ Authentication successful for user_id: {user_id}")
    return user_id

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the full user object from JWT token
    """
    user_id = get_current_user_id(credentials, db)
    user = db.query(User).filter(User.id == user_id).first()
    return user

# Alternative simplified version for testing (if you want to bypass some checks)
def get_current_user_id_simple(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Simplified version that only extracts user_id without database verification
    """
    try:
        print(f"Simple auth - token: {credentials.credentials[:20]}...")
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        
        if not user_id_str:
            raise HTTPException(status_code=401, detail="No user ID in token")
            
        user_id = int(user_id_str)
        print(f"Simple auth - user_id: {user_id}")
        return user_id
        
    except (JWTError, ValueError, TypeError) as e:
        print(f"Simple auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )