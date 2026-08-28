from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from collections import Counter
from app.database import get_db
from app.models import Tenant, Widget, Submission
from app.schemas import DashboardStats, SubmissionResponse
from app.auth import get_current_tenant

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics (Authenticated)"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Provides high-level analytics for the authenticated tenant's widgets and submissions."""
    # Widgets owned by tenant
    widgets = db.query(Widget).filter(Widget.tenant_id == tenant.id).all()
    widget_map = {w.id: w.name for w in widgets}
    total_widgets = len(widgets)

    # Submissions owned by tenant
    submissions = (
        db.query(Submission)
        .filter(Submission.tenant_id == tenant.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    total_submissions = len(submissions)

    # Aggregate by widget
    submissions_by_widget = Counter()
    for sub in submissions:
        w_name = widget_map.get(sub.widget_id, "Unknown Widget")
        submissions_by_widget[w_name] += 1

    # Aggregate by country
    submissions_by_country = Counter()
    for sub in submissions:
        country_name = sub.country or "Unknown / Direct"
        submissions_by_country[country_name] += 1

    # Recent submissions (up to 10)
    recent = submissions[:10]

    return DashboardStats(
        total_submissions=total_submissions,
        total_widgets=total_widgets,
        submissions_by_widget=dict(submissions_by_widget),
        submissions_by_country=dict(submissions_by_country),
        recent_submissions=[
            SubmissionResponse(
                id=s.id,
                widget_id=s.widget_id,
                tenant_id=s.tenant_id,
                payload=s.payload,
                ip_address=s.ip_address,
                country=s.country,
                city=s.city,
                geo_provider=s.geo_provider,
                created_at=s.created_at
            )
            for s in recent
        ]
    )


@router.get("/submissions", response_model=List[SubmissionResponse])
def get_submissions(
    widget_id: Optional[str] = Query(None, description="Optional widget filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns a paginated list of submissions for the authenticated tenant."""
    query = db.query(Submission).filter(Submission.tenant_id == tenant.id)

    if widget_id:
        query = query.filter(Submission.widget_id == widget_id)

    submissions = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit).all()

    return [
        SubmissionResponse(
            id=s.id,
            widget_id=s.widget_id,
            tenant_id=s.tenant_id,
            payload=s.payload,
            ip_address=s.ip_address,
            country=s.country,
            city=s.city,
            geo_provider=s.geo_provider,
            created_at=s.created_at
        )
        for s in submissions
    ]
