"""Celery tasks for asynchronous email sending."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_contact_notification(self, contact_message_id):
    """Send an HTML notification email when a new contact message arrives."""
    from django.conf import settings

    from .email import get_system_identity, render_template, send_html_email
    from .models import ContactMessage

    recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", None)
    if not recipient:
        return "CONTACT_NOTIFY_EMAIL not configured — skipped"

    try:
        msg = ContactMessage.objects.get(pk=contact_message_id)
    except ContactMessage.DoesNotExist:
        logger.warning("ContactMessage %s not found — skipping notification", contact_message_id)
        return "message not found"

    context = {
        "name": msg.name,
        "email": msg.email,
        "subject": msg.subject,
        "message": msg.message,
    }

    try:
        subject, html_body, text_body = render_template("contact_notification", context)
        send_html_email(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_identity=get_system_identity(),
            to_email=recipient,
        )
    except Exception as exc:
        logger.exception("Failed to send contact notification for message %s", contact_message_id)
        raise self.retry(exc=exc)

    return "sent"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_admin_reply(self, contact_message_id, reply_subject, reply_body, sent_by_id=None):
    """Send an admin reply to a contact message sender and log it."""
    from django.contrib.auth.models import User

    from .email import get_admin_identity, render_template, send_html_email
    from .models import ContactMessage, SentEmail

    try:
        msg = ContactMessage.objects.get(pk=contact_message_id)
    except ContactMessage.DoesNotExist:
        logger.warning("ContactMessage %s not found — skipping reply", contact_message_id)
        return "message not found"

    context = {
        "subject": msg.subject,
        "reply_body": reply_body,
        "original_message": msg.message,
        "name": msg.name,
    }

    from_identity = get_admin_identity()

    try:
        subject, html_body, text_body = render_template("admin_reply", context)
        # Allow overriding the default "Re: {subject}" if admin provided a custom subject
        if reply_subject:
            subject = reply_subject
        send_html_email(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_identity=from_identity,
            to_email=msg.email,
        )
    except Exception as exc:
        logger.exception("Failed to send admin reply for message %s", contact_message_id)
        raise self.retry(exc=exc)

    sent_by = None
    if sent_by_id:
        sent_by = User.objects.filter(pk=sent_by_id).first()

    SentEmail.objects.create(
        recipient_email=msg.email,
        recipient_name=msg.name,
        subject=subject,
        body_preview=reply_body[:500],
        from_identity=from_identity,
        contact_message=msg,
        sent_by=sent_by,
    )

    return "sent"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_admin_email(self, to_email, to_name, subject, body, sent_by_id=None):
    """Send a new email from admin (not a reply) and log it."""
    from django.contrib.auth.models import User

    from .email import get_admin_identity, render_template, send_html_email
    from .models import SentEmail

    context = {
        "subject": subject,
        "body": body,
        "name": to_name,
    }

    from_identity = get_admin_identity()

    try:
        rendered_subject, html_body, text_body = render_template("admin_new_email", context)
        send_html_email(
            subject=rendered_subject,
            html_body=html_body,
            text_body=text_body,
            from_identity=from_identity,
            to_email=to_email,
        )
    except Exception as exc:
        logger.exception("Failed to send admin email to %s", to_email)
        raise self.retry(exc=exc)

    sent_by = None
    if sent_by_id:
        sent_by = User.objects.filter(pk=sent_by_id).first()

    SentEmail.objects.create(
        recipient_email=to_email,
        recipient_name=to_name,
        subject=subject,
        body_preview=body[:500],
        from_identity=from_identity,
        sent_by=sent_by,
    )

    return "sent"
