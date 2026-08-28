from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Widget, Submission
from app.schemas import WidgetConfigResponse, SubmissionCreate, FormFieldSchema
from app.config import get_settings
from app.geo import enrich_ip
from app.rate_limiter import rate_limiter
from app.notifications import trigger_safe_side_effect

router = APIRouter(tags=["Public API (CORS Enabled)"])


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely, checking standard proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be a comma-separated list; first one is the client
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


@router.get("/widgets/{widget_id}/config", response_model=WidgetConfigResponse)
def get_widget_config(
    widget_id: str,
    response: Response,
    db: Session = Depends(get_db)
):
    """Public endpoint to fetch widget configuration for rendering in widget.js.
    Uses short-lived HTTP Cache-Control header (max-age=60).
    """
    widget = db.query(Widget).filter(Widget.id == widget_id).first()
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found."
        )

    # Set cache headers for fast CDN / browser caching
    response.headers["Cache-Control"] = "public, max-age=60"

    # Convert field definitions
    fields = [
        FormFieldSchema(
            name=f["name"],
            label=f.get("label", f["name"]),
            type=f.get("type", "text"),
            required=f.get("required", True)
        )
        for f in widget.fields_schema
    ]

    return WidgetConfigResponse(
        id=widget.id,
        widget_type=widget.widget_type,
        title=widget.title,
        description=widget.description,
        button_text=widget.button_text,
        primary_color=widget.primary_color,
        fields_schema=fields
    )


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_lead(
    request: Request,
    submission_in: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """Public submission endpoint for visitor form submissions.
    
    Security & Resilience Pipeline:
    1. Payload Size Guard (Rejects oversized payloads)
    2. Honeypot Spam Check (Blocks automated bots)
    3. Rate Limiting (Per client IP and per widget)
    4. Widget Validation (Ensures target widget exists)
    5. Form Validation (Checks required fields)
    6. Geo-IP Enrichment Fallback Chain (Provider A -> Provider B -> Degrade gracefully)
    7. Storage (Persists lead linked to widget and tenant)
    8. Safe Side-Effect (Notification that never breaks the submission)
    """
    settings = get_settings()

    # Step 1: Payload Size Check
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_PAYLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Payload exceeds maximum allowed size of {settings.MAX_PAYLOAD_SIZE_BYTES} bytes."
        )

    # Step 2: Honeypot Anti-Spam Check
    if submission_in.hp_trap and submission_in.hp_trap.strip():
        # Bots typically fill out all fields including hidden ones
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spam submission detected and rejected."
        )

    client_ip = get_client_ip(request)

    # Step 3: Rate Limiting
    rate_limiter.check_rate_limit(client_ip, submission_in.widget_id)

    # Step 4: Widget Lookup
    widget = db.query(Widget).filter(Widget.id == submission_in.widget_id).first()
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target widget does not exist."
        )

    # Step 5: Validate required fields against the widget schema
    for field in widget.fields_schema:
        field_name = field.get("name")
        is_required = field.get("required", False)
        if is_required:
            value = submission_in.data.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing required field: '{field.get('label', field_name)}'."
                )

    # Step 6: Geo Enrichment Fallback Chain
    country, city, geo_provider = await enrich_ip(client_ip)

    # Step 7: Store the Submission safely
    new_submission = Submission(
        widget_id=widget.id,
        tenant_id=widget.tenant_id,
        payload=submission_in.data,
        ip_address=client_ip,
        country=country,
        city=city,
        geo_provider=geo_provider
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    # Step 8: Safe Side-Effect (Notification / Webhook)
    trigger_safe_side_effect(new_submission.id, widget.title, submission_in.data)

    return {
        "status": "success",
        "submission_id": new_submission.id,
        "message": "Submission received successfully."
    }
