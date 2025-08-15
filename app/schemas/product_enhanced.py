# app/schemas/product_enhanced.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# ========== TEMPLATE CONFIGURATION ==========
class BusinessCategory(str, Enum):
    FOOD = "Food"
    CLOTHING = "Clothing"
    GENERAL = "General"

class TemplateType(str, Enum):
    TEMPLATE7 = "Template7"  # For Food vendors
    TEMPLATE8 = "Template8"  # For Clothing vendors
    DEFAULT = "Default"      # For other vendors

# Template mapping function
def get_template_for_category(business_category: str) -> str:
    """Return the appropriate template based on business category"""
    category_template_map = {
        BusinessCategory.FOOD: TemplateType.TEMPLATE7,
        BusinessCategory.CLOTHING: TemplateType.TEMPLATE8
    }
    return category_template_map.get(business_category, TemplateType.DEFAULT)

# ========== CLOTHING-SPECIFIC SCHEMAS (Template8) ==========
class ClothingSize(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    XXXL = "XXXL"

class ClothingType(str, Enum):
    COTTON = "Cotton"
    POLYESTER = "Polyester"
    WOOL = "Wool"
    SILK = "Silk"
    LINEN = "Linen"
    DENIM = "Denim"
    LEATHER = "Leather"
    SYNTHETIC = "Synthetic"

class ClothingCategory(str, Enum):
    SHIRTS = "Shirts"
    PANTS = "Pants"
    DRESSES = "Dresses"
    JACKETS = "Jackets"
    SHOES = "Shoes"
    ACCESSORIES = "Accessories"
    UNDERGARMENTS = "Undergarments"

class ClothingDetails(BaseModel):
    """Additional details specific to clothing products"""
    brand: str = Field(..., min_length=2, max_length=50)
    sizes: List[ClothingSize] = Field(..., min_items=1)
    colors: List[str] = Field(..., min_items=1, max_items=10)
    cloth_type: ClothingType
    clothing_category: ClothingCategory
    gender: Optional[str] = Field(None, pattern="^(Men|Women|Unisex|Kids)$")
    care_instructions: Optional[str] = Field(None, max_length=500)
    fabric_composition: Optional[str] = Field(None, max_length=200)
    country_of_origin: Optional[str] = Field(None, max_length=50)

# ========== FOOD-SPECIFIC SCHEMAS (Template7) ==========
class FoodCategory(str, Enum):
    APPETIZERS = "Appetizers"
    MAIN_COURSE = "Main Course"
    DESSERTS = "Desserts"
    BEVERAGES = "Beverages"
    SNACKS = "Snacks"
    BREAKFAST = "Breakfast"
    LUNCH = "Lunch"
    DINNER = "Dinner"

class CuisineType(str, Enum):
    INDIAN = "Indian"
    CHINESE = "Chinese"
    ITALIAN = "Italian"
    MEXICAN = "Mexican"
    AMERICAN = "American"
    THAI = "Thai"
    JAPANESE = "Japanese"
    CONTINENTAL = "Continental"
    FUSION = "Fusion"

class DietaryType(str, Enum):
    VEGETARIAN = "Vegetarian"
    VEGAN = "Vegan"
    NON_VEGETARIAN = "Non-Vegetarian"
    GLUTEN_FREE = "Gluten-Free"
    DAIRY_FREE = "Dairy-Free"
    KETO = "Keto"
    SUGAR_FREE = "Sugar-Free"

class SpiceLevel(str, Enum):
    MILD = "Mild"
    MEDIUM = "Medium"
    HOT = "Hot"
    EXTRA_HOT = "Extra Hot"

class FoodDetails(BaseModel):
    """Additional details specific to food products"""
    cuisine_type: CuisineType
    food_category: FoodCategory
    dietary_type: List[DietaryType] = Field(..., min_items=1)
    spice_level: Optional[SpiceLevel] = None
    ingredients: List[str] = Field(..., min_items=1, max_items=20)
    allergens: Optional[List[str]] = Field(None, max_items=10)
    preparation_time: Optional[int] = Field(None, ge=1, le=1440, description="Time in minutes")
    shelf_life: Optional[int] = Field(None, ge=1, description="Shelf life in days")
    storage_instructions: Optional[str] = Field(None, max_length=200)
    nutritional_info: Optional[Dict[str, Any]] = None  # calories, protein, carbs, etc.
    serving_size: Optional[str] = Field(None, max_length=50)

# ========== ENHANCED PRODUCT SCHEMAS ==========
# Keep your existing ProductCreate and add enhanced version
class EnhancedProductCreate(BaseModel):
    # Base fields (same as your existing ProductCreate)
    name: str
    description: str
    category: str
    stock: int
    price: float = 0.0
    pricing_tiers: List[Dict[str, Any]]  # Your existing pricing tiers
    image_urls: List[str] = []
    
    # Template-specific details
    clothing_details: Optional[ClothingDetails] = None
    food_details: Optional[FoodDetails] = None
    
    def validate_template_details(self, vendor_category: str):
        """Validate that template details match vendor category"""
        if vendor_category == BusinessCategory.CLOTHING:
            if not self.clothing_details:
                raise ValueError("Clothing details are required for clothing vendors")
        elif vendor_category == BusinessCategory.FOOD:
            if not self.food_details:
                raise ValueError("Food details are required for food vendors")

# Enhanced version of your existing ProductOut
class EnhancedProductOut(BaseModel):
    # All your existing fields
    id: int
    vendor_id: int
    name: str
    description: str
    category: str
    stock: int
    price: float
    image_urls: List[str]
    created_at: datetime
    pricing_tiers: List[Dict[str, Any]]
    
    # New template-specific fields
    template_type: str = "Default"
    clothing_details: Optional[Dict[str, Any]] = None
    food_details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# Enhanced version of your existing ProductUpdate
class EnhancedProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[float] = None
    pricing_tiers: Optional[List[Dict[str, Any]]] = None
    image_urls: Optional[List[str]] = None
    
    # Template-specific updates
    clothing_details: Optional[ClothingDetails] = None
    food_details: Optional[FoodDetails] = None
    
    class Config:
        from_attributes = True