# BUILDLOG.md — AI-Assisted Development Log

## 1. Project Planning & Architecture Design
- **Where AI helped**: Outlined the end-to-end architecture covering the 3 distinct actors (Widget Owner, External Host Website, Visitor) and designed the 5-step security & resilience submission pipeline.
- **Adjustments made**: Ensured the architecture remained clean, modular, and beginner-friendly using FastAPI, standard SQLAlchemy SQLite, and Pydantic v2 schemas without overly complex microservice overhead.

## 2. API Design & Boundary Validation
- **Where AI helped**: Drafted FastAPI routers for widget management (`/widgets`), public endpoints (`/widgets/{id}/config`, `/submissions`), and dashboard analytics (`/dashboard`).
- **Where AI was wrong / Issues encountered**: In Pydantic v2, defining a field starting with an underscore (like `_hp_trap`) directly raises a `NameError` ("Fields must not use names with leading underscores").
- **What was changed**: Refactored the honeypot field in `SubmissionCreate` to use `hp_trap: Optional[str] = Field(None, alias="_hp_trap")` with `model_config = ConfigDict(populate_by_name=True)` so client forms can post `_hp_trap` seamlessly while adhering strictly to Pydantic standards.

## 3. Resilience, Fallback Chain & Abuse Protection
- **Where AI helped**: Created the dual-provider IP geolocation fallback chain (`ip-api.com` -> `ipapi.co` -> graceful degradation) with configurable mock toggles (`MOCK_GEO_PROVIDER_A_DOWN`, `MOCK_GEO_PROVIDER_B_DOWN`).
- **Where AI helped**: Built an in-memory sliding-window rate limiter per `(client_ip, widget_id)` and safe side-effect error catching for email notifications.
- **Verification**: Wrote a complete test suite in `tests/test_probes.py` proving all 6 acceptance probes pass deterministically.

## 4. Embeddable JavaScript & Second-Origin Testing
- **Where AI helped**: Developed `app/static/widget.js` that automatically detects its script URL, fetches the widget's config from the backend, renders scoped CSS forms, and submits leads over CORS.
- **What was verified**: Created `test_customer_site/index.html` to simulate an external customer website running on a separate origin (`http://localhost:5500` or `file://`).
