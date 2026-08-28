# Embeddable Widget & Lead-Capture Platform

A resilient, multi-tenant backend built with **FastAPI** that allows customers to create embeddable lead capture widgets (signup forms, contact forms, popovers) and install them on any external website using a single `<script>` snippet.

When visitors interact with the widget on the public internet, submissions travel to our hardened submission pipeline where they are validated, protected against spam, enriched with geolocation data via a fallback chain, safely stored in SQLite, and displayed in the owner's dashboard.

---

## Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                1. WIDGET OWNER                                  |
|   (Authenticated via X-API-Key)                                                 |
|                                                                                 |
|   - POST /widgets               --> Create custom form & get embed snippet      |
|   - GET  /widgets               --> Manage existing widgets (tenant isolated)   |
|   - GET  /dashboard/stats       --> View conversion metrics & geo breakdown     |
|   - GET  /dashboard/submissions --> View collected leads                        |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                           2. EXTERNAL CUSTOMER SITE                             |
|   (Any Origin, e.g. http://localhost:5500 or file://)                           |
|                                                                                 |
|   1. Embeds: <script src="http://localhost:8000/static/widget.js?id=..."></script>
|   2. Fetches config: GET /widgets/{id}/config (Public, CORS, Cached max-age=60) |
|   3. Renders widget form dynamically into DOM                                   |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                       3. HARDENED SUBMISSION PIPELINE                           |
|   (POST /submissions - Public, CORS Enabled, Preflight Handled)                 |
|                                                                                 |
|   Step 1: Size & Boundary Validation (Max 64KB, required fields -> 4xx, no 500) |
|   Step 2: Honeypot Anti-Spam Check (_hp_trap filled -> 400 Bad Request)        |
|   Step 3: Sliding-Window Rate Limiting (5 req/min per IP/widget -> 429)        |
|   Step 4: Geo-IP Fallback Chain:                                                |
|           [ip-api.com] --(fails)--> [ipapi.co] --(fails)--> [Store without geo] |
|   Step 5: Store Submission in Database (Linked to tenant & widget)              |
|   Step 6: Safe Side-Effect Notification (Email logger - errors never break 200) |
+---------------------------------------------------------------------------------+
```

---

## Quick Start & Setup

### 1. Prerequisites
- Python 3.10+
- `pip`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create your local `.env` file (copied from `.env.example`):
```bash
cp .env.example .env
```

### 4. Seed the Database
Populate the database with a demo tenant, sample widgets, and initial submissions:
```bash
python seed.py
```
*Output will display the demo API Key (`demo-api-key-12345`) and created widget IDs.*

### 5. Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Base API: [http://localhost:8000](http://localhost:8000)

---

## Testing the Second-Origin Customer Site

To test the embed script running from a separate origin:

1. In a second terminal window, run a local web server inside `test_customer_site`:
   ```bash
   python -m http.server 5500 --directory test_customer_site
   ```
2. Open your browser to [http://localhost:5500](http://localhost:5500).
3. You will see the embedded form rendered dynamically via `<script src="http://localhost:8000/static/widget.js?id=demo-widget-newsletter"></script>`.
4. Fill out the form and submit. It communicates with the backend on port `8000` via CORS!

---

## Acceptance Probes & PyTest Suite

Run the automated test suite verifying all 6 acceptance probes from the Capstone Brief:

```bash
pytest tests/test_probes.py -v
```

### Probes Tested:
1. **Probe 1**: Valid submission from second origin -> stored in database and visible in dashboard.
2. **Probe 2**: Malformed & oversized payloads (>64KB) -> clean `4xx` JSON errors, never a `500`.
3. **Probe 3**: Rapid burst of submissions -> `429 Too Many Requests` returned, subsequent normal requests still succeed.
4. **Probe 4**: Geolocation fallback chain -> Provider A down falls back to Provider B; both down still stores submission gracefully.
5. **Probe 5**: Notification side effect failure -> safely caught and logged, submission still returns success.
6. **Probe 6**: Honeypot spam trap -> bot submissions with `_hp_trap` filled are blocked with `400`.

---

## API Documentation

### Public Endpoints (CORS Enabled)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status and health check |
| `GET` | `/widget.js` | Embeddable JavaScript bundle (`Cache-Control: max-age=3600`) |
| `GET` | `/widgets/{id}/config` | Public widget config (`Cache-Control: max-age=60`) |
| `POST` | `/submissions` | Public submission endpoint with rate limiting & anti-spam |

#### Example: Submit Lead (`POST /submissions`)
```bash
curl -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "widget_id": "demo-widget-newsletter",
    "data": {
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  }'
```

---

### Authenticated Endpoints (Requires `X-API-Key: demo-api-key-12345`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/widgets` | Create a new widget |
| `GET` | `/widgets` | List all widgets owned by tenant |
| `GET` | `/widgets/{id}` | Get widget details + embed snippet |
| `PUT` | `/widgets/{id}` | Update widget configuration |
| `DELETE` | `/widgets/{id}` | Delete widget and submissions |
| `GET` | `/dashboard/stats` | Analytics summary (counts, country breakdown) |
| `GET` | `/dashboard/submissions` | List collected lead submissions |

#### Example: Get Dashboard Analytics
```bash
curl -X GET http://localhost:8000/dashboard/stats \
  -H "X-API-Key: demo-api-key-12345"
```

---

## Honest Limitations & Future Improvements

1. **In-Memory Rate Limiting**: The current rate limiter uses an in-memory sliding window. For multi-node distributed deployments, this would be backed by Redis.
2. **Local SQLite Database**: SQLite is used for zero-configuration local development. For high-concurrency production deployments, swap `DATABASE_URL` in `.env` to PostgreSQL.
3. **Mock Email Provider**: Lead notification emails are currently logged to console (with a toggleable exception trigger for tests). In production, connect an SMTP service (e.g., Mailgun/SendGrid or local Mailpit).
