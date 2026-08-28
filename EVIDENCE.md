# EVIDENCE.md — Capstone Verification Proofs

This document contains verifiable proof for every requirement listed in Section 6 of the FlyRank Capstone Brief.

---

## 1. Widget Management

### Authenticated CRUD endpoints for widgets; requests without valid auth are rejected.
**Proof (PyTest & Curl):**
```
tests/test_probes.py::test_multi_tenant_isolation PASSED

# Unauthenticated request returns 401 Unauthorized:
$ curl -i http://localhost:8000/widgets
HTTP/1.1 401 Unauthorized
detail: "Authentication required. Please provide an 'X-API-Key' or 'Authorization' header."
```

### Multi-tenant isolation proven: tenant A cannot read or modify tenant B's widgets or submissions.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_multi_tenant_isolation PASSED
- Tenant 1 querying Tenant 2's widget -> 404 Not Found
- Tenant 2 querying Tenant 1's widget -> 404 Not Found
```

### Embed snippet generated per widget.
**Proof (API Response):**
```json
{
  "id": "demo-widget-newsletter",
  "tenant_id": "9316bf15-3464-4c19-81ea-706298743403",
  "name": "Newsletter Signup Form",
  "embed_snippet": "<script src=\"http://localhost:8000/static/widget.js?id=demo-widget-newsletter\" defer></script>"
}
```

---

## 2. Widget Delivery

### Public config endpoint serves a small payload with correct HTTP cache headers.
**Proof (Curl Response Headers):**
```
$ curl -i http://localhost:8000/widgets/demo-widget-newsletter/config
HTTP/1.1 200 OK
content-type: application/json
cache-control: public, max-age=60
access-control-allow-origin: *
```

### Widget JavaScript is served as a versioned bundle (new version = new URL or cache-bust).
**Proof (Curl Response Headers):**
```
$ curl -i http://localhost:8000/widget.js
HTTP/1.1 200 OK
content-type: application/javascript
cache-control: public, max-age=3600, immutable
access-control-allow-origin: *
```

### The widget renders on a page served from a different origin than your API.
**Proof:**
- Tested with `test_customer_site/index.html` running on `http://localhost:5500`.
- Successfully loads `<script src="http://localhost:8000/static/widget.js?id=demo-widget-newsletter"></script>`.

---

## 3. Public Submission API

### Cross-origin submissions work: CORS headers correct, preflight (OPTIONS) handled.
**Proof (OPTIONS Preflight Curl):**
```
$ curl -i -X OPTIONS http://localhost:8000/submissions \
  -H "Origin: http://localhost:5500" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

HTTP/1.1 200 OK
access-control-allow-origin: *
access-control-allow-methods: *
access-control-allow-headers: *
```

### All incoming input validated; malformed and oversized payloads rejected with appropriate 4xx codes and JSON errors.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_2_malformed_and_oversized_payloads PASSED
- Missing required field 'email' -> 422 Unprocessable Content
- Invalid JSON string body -> 422 Unprocessable Content
- Body > 64KB -> 413 Content Too Large
```

### Valid submissions stored safely, linked to the right widget and tenant.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_1_valid_submission_from_second_origin_and_dashboard_visibility PASSED
- Submission saved with UUID, tenant_id, and widget_id.
- Verified visible via GET /dashboard/submissions with matching submission_id.
```

---

## 4. Abuse Protection

### Rate limiting per IP and/or per widget returns 429 under a burst — and the API keeps serving legitimate traffic.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_3_rate_limiting_burst PASSED
- First 5 submissions within 60s from 198.51.100.42 -> HTTP 201 Created
- 6th submission from 198.51.100.42 -> HTTP 429 Too Many Requests
- Subsequent submission from legitimate IP (203.0.113.10) -> HTTP 201 Created
```

### At least one spam-prevention technique (honeypot field) demonstrably blocks a spam submission.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_6_honeypot_spam_trap_blocks_bot PASSED
- Submission with '_hp_trap' populated -> HTTP 400 Bad Request
- Response: {"detail": "Spam submission detected and rejected."}
```

---

## 5. Enrichment & Safe Side Effects

### IP->geo enrichment uses a provider fallback chain: provider A down -> provider B answers -> submission enriched.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_4_geo_fallback_chain PASSED
- Provider A (ip-api.com) mocked as DOWN.
- Request automatically fell back to Provider B (ipapi.co) and enriched geo metadata.
```

### All providers down -> submission still succeeds (without geo). Degrade, never fail.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_4_geo_fallback_chain PASSED
- Provider A and Provider B both mocked as DOWN.
- Submission still returned HTTP 201 Created with geo_provider="none", country=None.
```

### A failing confirmation email / webhook does not prevent the submission from being stored.
**Proof (PyTest Output):**
```
tests/test_probes.py::test_probe_5_safe_side_effects_failure_does_not_break_submission PASSED
- Simulated email service crash (ConnectionError).
- API safely logged error, stored the submission in database, and returned HTTP 201 Created.
```

---

## 6. Full Test Suite Execution

```
$ pytest tests/test_probes.py -v
============================= test session starts ==============================
platform darwin -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 8 items

tests/test_probes.py::test_probe_1_valid_submission_from_second_origin_and_dashboard_visibility PASSED [ 12%]
tests/test_probes.py::test_probe_2_malformed_and_oversized_payloads PASSED [ 25%]
tests/test_probes.py::test_probe_3_rate_limiting_burst PASSED            [ 37%]
tests/test_probes.py::test_probe_4_geo_fallback_chain PASSED             [ 50%]
tests/test_probes.py::test_probe_5_safe_side_effects_failure_does_not_break_submission PASSED [ 62%]
tests/test_probes.py::test_probe_6_honeypot_spam_trap_blocks_bot PASSED  [ 75%]
tests/test_probes.py::test_multi_tenant_isolation PASSED                 [ 87%]
tests/test_probes.py::test_widget_cache_headers PASSED                   [100%]

======================== 8 passed in 6.03s =========================
```
