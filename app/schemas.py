from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# --- Widget Field Schema ---
class FormFieldSchema(BaseModel):
    name: str = Field(..., description="Field identifier/key, e.g., 'email'")
    label: str = Field(..., description="Display label, e.g., 'Email Address'")
    type: str = Field(default="text", description="Field type: text, email, tel, textarea")
    required: bool = Field(default=True, description="Whether the field is mandatory")


# --- Widget Schemas ---
class WidgetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Internal widget name")
    widget_type: str = Field(default="signup", description="signup, contact, or popover")
    title: str = Field(default="Join Our Newsletter", max_length=200)
    description: str = Field(default="Subscribe for updates.", max_length=500)
    button_text: str = Field(default="Submit", max_length=50)
    primary_color: str = Field(default="#4F46E5", max_length=20)
    fields_schema: List[FormFieldSchema] = Field(
        default_factory=lambda: [
            FormFieldSchema(name="email", label="Email Address", type="email", required=True)
        ]
    )


class WidgetCreate(WidgetBase):
    pass


class WidgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    widget_type: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    button_text: Optional[str] = Field(None, max_length=50)
    primary_color: Optional[str] = None
    fields_schema: Optional[List[FormFieldSchema]] = None


class WidgetResponse(WidgetBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    embed_snippet: str

    model_config = ConfigDict(from_attributes=True)


class WidgetConfigResponse(BaseModel):
    """Public schema served to the frontend widget.js."""
    id: str
    widget_type: str
    title: str
    description: str
    button_text: str
    primary_color: str
    fields_schema: List[FormFieldSchema]


# --- Submission Schemas ---
class SubmissionCreate(BaseModel):
    widget_id: str = Field(..., description="The ID of the widget being submitted to")
    data: Dict[str, Any] = Field(..., description="Form field values submitted by user")
    hp_trap: Optional[str] = Field(
        default=None,
        alias="_hp_trap",
        description="Honeypot field. Must be empty for legitimate human visitors."
    )

    model_config = ConfigDict(populate_by_name=True)


class SubmissionResponse(BaseModel):
    id: str
    widget_id: str
    tenant_id: str
    payload: Dict[str, Any]
    ip_address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    geo_provider: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Dashboard Analytics Schema ---
class DashboardStats(BaseModel):
    total_submissions: int
    total_widgets: int
    submissions_by_widget: Dict[str, int]
    submissions_by_country: Dict[str, int]
    recent_submissions: List[SubmissionResponse]
