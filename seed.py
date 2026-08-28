"""
Seed script to create a demo tenant, widgets, and sample submissions.
Run with: python seed.py
"""
import uuid
from datetime import datetime, timezone
from app.database import SessionLocal, engine, Base
from app.models import Tenant, Widget, Submission

# Ensure all tables exist
Base.metadata.create_all(bind=engine)


def seed_database():
    db = SessionLocal()
    try:
        print("🌱 Seeding database with demo data...")

        # 1. Clean existing demo data if any
        existing_tenant = db.query(Tenant).filter(Tenant.api_key == "demo-api-key-12345").first()
        if existing_tenant:
            print("ℹ️ Existing demo tenant found. Resetting...")
            db.delete(existing_tenant)
            db.commit()

        # 2. Create Demo Tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Acme Marketing Corp",
            api_key="demo-api-key-12345",
            created_at=datetime.now(timezone.utc)
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # 3. Create Sample Widget 1: Newsletter Signup
        widget_signup = Widget(
            id="demo-widget-newsletter",
            tenant_id=tenant.id,
            name="Newsletter Signup Form",
            widget_type="signup",
            title="Get Weekly Growth Insights",
            description="Subscribe to receive our curated tech articles directly to your inbox.",
            button_text="Subscribe Now",
            primary_color="#4F46E5",
            fields_schema=[
                {"name": "name", "label": "Your Name", "type": "text", "required": True},
                {"name": "email", "label": "Work Email", "type": "email", "required": True}
            ],
            created_at=datetime.now(timezone.utc)
        )
        db.add(widget_signup)

        # 4. Create Sample Widget 2: Contact Us Popover
        widget_contact = Widget(
            id="demo-widget-contact",
            tenant_id=tenant.id,
            name="Sales Contact Popover",
            widget_type="popover",
            title="Chat With Our Sales Team",
            description="Leave a message and an expert will get back to you within 2 hours.",
            button_text="Send Message",
            primary_color="#059669",
            fields_schema=[
                {"name": "name", "label": "Full Name", "type": "text", "required": True},
                {"name": "email", "label": "Email Address", "type": "email", "required": True},
                {"name": "message", "label": "Your Message", "type": "textarea", "required": True}
            ],
            created_at=datetime.now(timezone.utc)
        )
        db.add(widget_contact)
        db.commit()

        # 5. Create Sample Submissions for the widgets
        sample_submissions = [
            Submission(
                widget_id=widget_signup.id,
                tenant_id=tenant.id,
                payload={"name": "Alice Johnson", "email": "alice@example.com"},
                ip_address="8.8.8.8",
                country="United States",
                city="Ashburn",
                geo_provider="ip-api.com",
                created_at=datetime.now(timezone.utc)
            ),
            Submission(
                widget_id=widget_signup.id,
                tenant_id=tenant.id,
                payload={"name": "Bob Smith", "email": "bob@example.co.uk"},
                ip_address="212.58.244.20",
                country="United Kingdom",
                city="London",
                geo_provider="ipapi.co",
                created_at=datetime.now(timezone.utc)
            ),
            Submission(
                widget_id=widget_contact.id,
                tenant_id=tenant.id,
                payload={"name": "Carlos Gomez", "email": "carlos@startup.es", "message": "Interested in enterprise pricing."},
                ip_address="80.58.67.250",
                country="Spain",
                city="Madrid",
                geo_provider="ip-api.com",
                created_at=datetime.now(timezone.utc)
            )
        ]

        db.add_all(sample_submissions)
        db.commit()

        print("\n✅ Seeding Complete!")
        print("--------------------------------------------------")
        print(f"🔑 Demo Tenant API Key : demo-api-key-12345")
        print(f"📦 Demo Tenant ID      : {tenant.id}")
        print(f"📝 Widget 1 (Signup)   : {widget_signup.id}")
        print(f"💬 Widget 2 (Popover)  : {widget_contact.id}")
        print(f"📊 Sample Submissions  : {len(sample_submissions)} records created")
        print("--------------------------------------------------\n")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
