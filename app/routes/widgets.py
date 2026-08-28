from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Widget, Tenant
from app.schemas import WidgetCreate, WidgetUpdate, WidgetResponse
from app.auth import get_current_tenant
from app.config import get_settings

router = APIRouter(prefix="/widgets", tags=["Widgets (Authenticated)"])


def format_widget_response(widget: Widget) -> WidgetResponse:
    """Helper to convert database Widget to response schema including the HTML embed snippet."""
    settings = get_settings()
    snippet = f'<script src="{settings.BASE_URL}/static/widget.js?id={widget.id}" defer></script>'
    
    return WidgetResponse(
        id=widget.id,
        tenant_id=widget.tenant_id,
        name=widget.name,
        widget_type=widget.widget_type,
        title=widget.title,
        description=widget.description,
        button_text=widget.button_text,
        primary_color=widget.primary_color,
        fields_schema=widget.fields_schema,
        created_at=widget.created_at,
        updated_at=widget.updated_at,
        embed_snippet=snippet
    )


@router.post("", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
def create_widget(
    widget_in: WidgetCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Creates a new widget tied to the authenticated tenant."""
    # Convert Pydantic fields to JSON serializable dictionaries
    fields_data = [f.model_dump() for f in widget_in.fields_schema]

    new_widget = Widget(
        tenant_id=tenant.id,
        name=widget_in.name,
        widget_type=widget_in.widget_type,
        title=widget_in.title,
        description=widget_in.description,
        button_text=widget_in.button_text,
        primary_color=widget_in.primary_color,
        fields_schema=fields_data,
    )
    db.add(new_widget)
    db.commit()
    db.refresh(new_widget)
    return format_widget_response(new_widget)


@router.get("", response_model=List[WidgetResponse])
def list_widgets(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Lists all widgets owned by the authenticated tenant."""
    widgets = db.query(Widget).filter(Widget.tenant_id == tenant.id).all()
    return [format_widget_response(w) for w in widgets]


@router.get("/{widget_id}", response_model=WidgetResponse)
def get_widget(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Fetches a single widget by ID. Enforces strict tenant isolation."""
    widget = db.query(Widget).filter(
        Widget.id == widget_id,
        Widget.tenant_id == tenant.id
    ).first()

    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or you do not have permission to access it."
        )

    return format_widget_response(widget)


@router.put("/{widget_id}", response_model=WidgetResponse)
def update_widget(
    widget_id: str,
    widget_update: WidgetUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Updates an existing widget. Enforces tenant isolation."""
    widget = db.query(Widget).filter(
        Widget.id == widget_id,
        Widget.tenant_id == tenant.id
    ).first()

    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or you do not have permission to edit it."
        )

    update_data = widget_update.model_dump(exclude_unset=True)
    if "fields_schema" in update_data and update_data["fields_schema"] is not None:
        update_data["fields_schema"] = [
            f.model_dump() if hasattr(f, "model_dump") else f for f in update_data["fields_schema"]
        ]

    for key, value in update_data.items():
        setattr(widget, key, value)

    db.commit()
    db.refresh(widget)
    return format_widget_response(widget)


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Deletes a widget and all its associated submissions."""
    widget = db.query(Widget).filter(
        Widget.id == widget_id,
        Widget.tenant_id == tenant.id
    ).first()

    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or you do not have permission to delete it."
        )

    db.delete(widget)
    db.commit()
    return None
