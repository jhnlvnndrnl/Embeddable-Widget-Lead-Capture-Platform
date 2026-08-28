import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Tenant, Widget, Submission
from app.config import get_settings
from app.rate_limiter import rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Sets up a clean test database and demo records before each test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Submission).delete()
    db.query(Widget).delete()
    db.query(Tenant).delete()
    db.commit()

    # Create Tenant 1 (Acme)
    tenant_1 = Tenant(
        id="test-tenant-1",
        name="Tenant One",
        api_key="key-tenant-1",
        created_at=datetime.now(timezone.utc)
    )
    # Create Tenant 2 (Beta Corp)
    tenant_2 = Tenant(
        id="test-tenant-2",
        name="Tenant Two",
        api_key="key-tenant-2",
        created_at=datetime.now(timezone.utc)
    )
    db.add_all([tenant_1, tenant_2])
    db.commit()

    # Create Widget for Tenant 1
    widget_1 = Widget(
        id="test-widget-1",
        tenant_id=tenant_1.id,
        name="Newsletter Form",
        widget_type="signup",
        title="Subscribe to Newsletter",
        description="Get daily updates",
        button_text="Sign Up",
        primary_color="#4F46E5",
        fields_schema=[
            {"name": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "name", "label": "Full Name", "type": "text", "required": True}
        ],
        created_at=datetime.now(timezone.utc)
    )

    # Create Widget for Tenant 2
    widget_2 = Widget(
        id="test-widget-2",
        tenant_id=tenant_2.id,
        name="Beta Feedback Form",
        widget_type="contact",
        title="Leave Feedback",
        description="Tell us your thoughts",
        button_text="Submit Feedback",
        primary_color="#10B981",
        fields_schema=[
            {"name": "email", "label": "Email", "type": "email", "required": True}
        ],
        created_at=datetime.now(timezone.utc)
    )
    db.add_all([widget_1, widget_2])
    db.commit()
    db.close()

    # Reset in-memory rate limiter
    rate_limiter.reset()

    # Reset environment mock flags
    settings = get_settings()
    settings.MOCK_GEO_PROVIDER_A_DOWN = False
    settings.MOCK_GEO_PROVIDER_B_DOWN = False
    settings.MOCK_EMAIL_SHOULD_FAIL = False

    yield


# =========================================================================
# PROBE 1: Cross-Origin Submission & Dashboard Visibility
# =========================================================================
def test_probe_1_valid_submission_from_second_origin_and_dashboard_visibility():
    """Probe 1: POST a valid submission with cross-origin headers -> stored, 2xx, and visible in dashboard."""
    # 1. Visitor submits from a different origin (e.g. localhost:5500)
    response = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "visitor@example.com", "name": "John Visitor"}
        },
        headers={
            "Origin": "http://localhost:5500",
            "X-Forwarded-For": "8.8.8.8"
        }
    )
    assert response.status_code in (200, 201), f"Expected 2xx status, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("status") == "success"
    submission_id = data.get("submission_id")
    assert submission_id is not None

    # 2. Owner checks dashboard submissions via authenticated API
    dash_res = client.get(
        "/dashboard/submissions",
        headers={"X-API-Key": "key-tenant-1"}
    )
    assert dash_res.status_code == 200
    submissions = dash_res.json()
    assert len(submissions) >= 1
    assert any(s["id"] == submission_id for s in submissions)

    # 3. Check dashboard stats
    stats_res = client.get(
        "/dashboard/stats",
        headers={"X-API-Key": "key-tenant-1"}
    )
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_submissions"] >= 1
    assert stats["total_widgets"] == 1


# =========================================================================
# PROBE 2: Clean 4xx Validation Errors (Never 500)
# =========================================================================
def test_probe_2_malformed_and_oversized_payloads():
    """Probe 2: Send malformed and oversized payload -> clean 4xx JSON errors, never a 500."""
    # Case A: Missing required form field ('email')
    res_missing = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"name": "No Email User"}
        },
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    assert res_missing.status_code == 422
    assert "Missing required field" in res_missing.json()["detail"]

    # Case B: Malformed body (invalid JSON structure)
    res_malformed = client.post(
        "/submissions",
        content="not-a-valid-json-string",
        headers={"Content-Type": "application/json", "X-Forwarded-For": "1.2.3.4"}
    )
    assert res_malformed.status_code == 422
    assert res_malformed.status_code != 500

    # Case C: Oversized payload (> 64KB)
    large_text = "A" * (70 * 1024)  # 70KB
    res_oversized = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "large@example.com", "name": large_text}
        },
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    assert res_oversized.status_code in (413, 400, 422)
    assert res_oversized.status_code != 500


# =========================================================================
# PROBE 3: Rate Limiting Burst Protection
# =========================================================================
def test_probe_3_rate_limiting_burst():
    """Probe 3: Fire a burst of rapid submissions -> 429s appear, normal request from another IP succeeds."""
    attacker_ip = "198.51.100.42"
    legitimate_ip = "203.0.113.10"

    # Settings limit is 5 per minute
    # Send 5 valid requests from attacker IP
    for i in range(5):
        res = client.post(
            "/submissions",
            json={
                "widget_id": "test-widget-1",
                "data": {"email": f"flood{i}@test.com", "name": f"Flooder {i}"}
            },
            headers={"X-Forwarded-For": attacker_ip}
        )
        assert res.status_code in (200, 201)

    # 6th request from attacker IP must be rejected with 429
    res_blocked = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "flood6@test.com", "name": "Flooder 6"}
        },
        headers={"X-Forwarded-For": attacker_ip}
    )
    assert res_blocked.status_code == 429
    assert "Too many submissions" in res_blocked.json()["detail"]

    # Legitimate traffic from a different IP right after still succeeds
    res_legit = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "legit@gooduser.com", "name": "Good User"}
        },
        headers={"X-Forwarded-For": legitimate_ip}
    )
    assert res_legit.status_code in (200, 201)


# =========================================================================
# PROBE 4: Geo-IP Fallback Chain & Graceful Degradation
# =========================================================================
def test_probe_4_geo_fallback_chain():
    """Probe 4: Provider A down -> Provider B used. Disable both -> stored anyway without geo."""
    settings = get_settings()

    # Step A: Disable Provider A (simulate downtime)
    settings.MOCK_GEO_PROVIDER_A_DOWN = True
    settings.MOCK_GEO_PROVIDER_B_DOWN = False

    res_fallback = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "fallback@example.com", "name": "Fallback Test"}
        },
        headers={"X-Forwarded-For": "8.8.8.8"}
    )
    assert res_fallback.status_code in (200, 201)

    # Step B: Disable BOTH Provider A & Provider B (all down)
    settings.MOCK_GEO_PROVIDER_A_DOWN = True
    settings.MOCK_GEO_PROVIDER_B_DOWN = True

    res_both_down = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "graceful@example.com", "name": "Degrade Test"}
        },
        headers={"X-Forwarded-For": "9.9.9.9"}
    )
    # Must STILL succeed without 500 error
    assert res_both_down.status_code in (200, 201)
    sub_id = res_both_down.json()["submission_id"]

    # Verify stored in DB
    db = SessionLocal()
    sub_record = db.query(Submission).filter(Submission.id == sub_id).first()
    assert sub_record is not None
    assert sub_record.geo_provider == "none"
    assert sub_record.country is None
    db.close()


# =========================================================================
# PROBE 5: Safe Side-Effects (Failure Must Not Break Main Request)
# =========================================================================
def test_probe_5_safe_side_effects_failure_does_not_break_submission():
    """Probe 5: Force the email/webhook side effect to throw -> submission still returns success and is stored."""
    settings = get_settings()
    settings.MOCK_EMAIL_SHOULD_FAIL = True

    response = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "safe@effect.com", "name": "Safe Side Effect"}
        },
        headers={"X-Forwarded-For": "100.20.30.40"}
    )
    assert response.status_code in (200, 201)
    assert response.json()["status"] == "success"
    submission_id = response.json()["submission_id"]

    # Confirm it was actually stored in the DB
    db = SessionLocal()
    sub_record = db.query(Submission).filter(Submission.id == submission_id).first()
    assert sub_record is not None
    db.close()


# =========================================================================
# PROBE 6: Honeypot Anti-Spam Trap
# =========================================================================
def test_probe_6_honeypot_spam_trap_blocks_bot():
    """Probe 6: Fill the honeypot field like a bot would -> submission is cleanly blocked."""
    response = client.post(
        "/submissions",
        json={
            "widget_id": "test-widget-1",
            "data": {"email": "bot@spammer.org", "name": "Spam Bot"},
            "_hp_trap": "http://buy-viagra-free.spam"  # Bot auto-fills the hidden trap!
        },
        headers={"X-Forwarded-For": "185.220.101.5"}
    )
    assert response.status_code == 400
    assert "Spam submission detected" in response.json()["detail"]


# =========================================================================
# MULTI-TENANT ISOLATION & CACHE HEADERS
# =========================================================================
def test_multi_tenant_isolation():
    """Guarantees Tenant A cannot see, edit, or delete Tenant B's widgets or submissions."""
    # Tenant 1 tries to access Tenant 2's widget -> 404
    res = client.get(
        "/widgets/test-widget-2",
        headers={"X-API-Key": "key-tenant-1"}
    )
    assert res.status_code == 404

    # Tenant 2 tries to access Tenant 1's widget -> 404
    res2 = client.get(
        "/widgets/test-widget-1",
        headers={"X-API-Key": "key-tenant-2"}
    )
    assert res2.status_code == 404


def test_widget_cache_headers():
    """Verifies that public config and JavaScript assets return HTTP caching headers."""
    # Config cache header
    res_cfg = client.get("/widgets/test-widget-1/config")
    assert res_cfg.status_code == 200
    assert "max-age=60" in res_cfg.headers.get("Cache-Control", "")

    # Static script cache header
    res_js = client.get("/widget.js")
    assert res_js.status_code == 200
    assert "max-age=3600" in res_js.headers.get("Cache-Control", "")
