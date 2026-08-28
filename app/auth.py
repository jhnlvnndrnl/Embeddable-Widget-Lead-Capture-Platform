from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Tenant


def get_current_tenant(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> Tenant:
    """Dependency to authenticate tenants via API Key.
    Supports either:
    1. 'X-API-Key: <api_key>' header
    2. 'Authorization: Bearer <api_key>' header

    Guarantees strict tenant isolation by returning the authenticated Tenant.
    """
    token = None
    if x_api_key:
        token = x_api_key.strip()
    elif authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
        else:
            token = authorization.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide an 'X-API-Key' or 'Authorization' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant = db.query(Tenant).filter(Tenant.api_key == token).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key. Access denied.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return tenant
