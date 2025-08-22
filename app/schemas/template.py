# app/schemas/template.py  
from pydantic import BaseModel
from typing import Optional, List

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    exists: bool
    preview_url: str

class TemplateSelectionRequest(BaseModel):
    template_id: int

class WebsiteInfo(BaseModel):
    subdomain: Optional[str]
    website_url: Optional[str]
    template_id: Optional[int]
    template_type: Optional[str]
    website_status: str
    domain_type: str
    went_live_at: Optional[str]
    readiness_score: int
    can_go_live: bool
    next_steps: List[str]