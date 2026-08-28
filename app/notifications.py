import logging
from app.config import get_settings

logger = logging.getLogger("notifications")


def trigger_safe_side_effect(submission_id: str, widget_title: str, payload: dict) -> bool:
    """Dispatches a secondary side-effect (e.g. sending a lead notification email / webhook).
    
    CRITICAL RULE:
    Non-critical operations must NEVER break the main submission path.
    Any exception or service failure is caught and logged safely, ensuring
    the visitor receives an HTTP 200/201 and data is stored.
    """
    settings = get_settings()

    try:
        if settings.MOCK_EMAIL_SHOULD_FAIL:
            raise ConnectionError("[Simulated Failure] External Email Service (SMTP/Mailgun) unreachable!")

        # Normal side-effect behavior (logs lead notification)
        logger.info(
            f" [Lead Notification Sent] Widget: '{widget_title}' | "
            f"Submission ID: {submission_id} | Payload: {payload}"
        )
        return True

    except Exception as exc:
        logger.error(
            f"⚠️ [Safe Side-Effect Error Caught] Failed to send notification for submission {submission_id}: {exc}"
        )
        # Return False to indicate the side effect failed, but do NOT re-raise
        return False
