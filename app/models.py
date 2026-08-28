import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    """Represents a customer account (multi-tenancy isolation)."""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    widgets = relationship("Widget", back_populates="tenant", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="tenant", cascade="all, delete-orphan")


class Widget(Base):
    """Represents an embeddable widget configured by a tenant."""
    __tablename__ = "widgets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    widget_type = Column(String(50), default="signup", nullable=False)  # signup, contact, popover
    title = Column(String(200), nullable=False, default="Join Our Newsletter")
    description = Column(String(500), nullable=False, default="Subscribe to get our latest news & updates.")
    button_text = Column(String(50), nullable=False, default="Submit")
    primary_color = Column(String(20), nullable=False, default="#4F46E5")
    
    # Dynamic form fields list: [{"name": "email", "label": "Email Address", "type": "email", "required": true}]
    fields_schema = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="widgets")
    submissions = relationship("Submission", back_populates="widget", cascade="all, delete-orphan")


class Submission(Base):
    """Represents a lead/form submission collected from an embedded widget."""
    __tablename__ = "submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    widget_id = Column(String(36), ForeignKey("widgets.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Store dynamic submitted key-value pairs (e.g. {"email": "alex@example.com", "name": "Alex"})
    payload = Column(JSON, nullable=False, default=dict)
    
    ip_address = Column(String(45), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    geo_provider = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="submissions")
    widget = relationship("Widget", back_populates="submissions")
