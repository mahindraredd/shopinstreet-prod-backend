# app/main.py - Cleaned version

from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Database imports
from app.db.session import engine, Base, SessionLocal
from app.core.database_optimizer import create_enterprise_indexes

# Model imports (needed for SQLAlchemy relationships)
from app.models.domain import VendorDomain, DomainSuggestion
from app.models.order import Order

# Middleware
from app.middleware.subdomain_middleware import SubdomainMiddleware

# API Routes
from app.api.routes_vendor import router as vendor_router
from app.api.routes_product import router as product_router
from app.api.routes_order import router as order_router
from app.api.routes_vendor_store import router as vendor_store_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_ai import router as ai_router
from app.api import routes_business_profile
from app.api.routes_domain import router as domain_router
from app.api.routes_review import router as review_router
from app.routers import users, cart

# Create FastAPI app
app = FastAPI(
    title="vendor-product-api",
    description="basically it has all the details of the vendor and product",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace * with your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SubdomainMiddleware)

# Create database tables
Base.metadata.create_all(bind=engine)

# Register API routes
app.include_router(vendor_router, prefix="/api/vendor", tags=["Vendor"])
app.include_router(product_router, prefix="/api/products", tags=["Product"])
app.include_router(order_router, prefix="/api/orders", tags=["Order"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Product Extraction"])
app.include_router(review_router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(routes_business_profile.router, prefix="/api/business-profile", tags=["Business Profile"])
app.include_router(domain_router, prefix="/api/domains", tags=["Domains"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(vendor_store_router, prefix="/api")

# Mount static files for deployed sites
app.mount("/static_sites", StaticFiles(directory="static_sites"), name="static_sites")

@app.get("/")
async def handle_root(request: Request):
    """Handle root requests - both main domain and subdomains"""
    subdomain = getattr(request.state, 'subdomain', None)
    
    if subdomain:
        # This is a subdomain request - middleware should have handled it
        # If we reach here, subdomain exists but no template is deployed
        return HTMLResponse("""
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>Website Coming Soon!</h1>
                <p>This website is being set up. Please check back soon.</p>
            </body>
        </html>
        """)
    else:
        # Main domain - show your main application
        return {
            "message": "Welcome to ShopInStreet API",
            "docs": "/docs",
            "status": "operational"
        }

def create_indexes():
    db = SessionLocal()
    try:
        create_enterprise_indexes(db)
    finally:
        db.close()

create_indexes()

# Custom OpenAPI with Bearer Auth
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Vendor Backend API",
        version="1.0.0",
        description="API for vendors to manage registration, login, and products.",
        routes=app.routes,
    )

    # Add Bearer auth globally
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi