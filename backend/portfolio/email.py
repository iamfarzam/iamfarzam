"""Email rendering utilities and sender identity helpers."""

import re
from html.parser import HTMLParser
from io import StringIO

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template


# ---------------------------------------------------------------------------
# Sender identity helpers
# ---------------------------------------------------------------------------

def get_system_identity():
    """Return the system (noreply) sender identity string."""
    name = getattr(settings, "SYSTEM_EMAIL_NAME", "Portfolio")
    email = settings.DEFAULT_FROM_EMAIL
    return f"{name} <{email}>"


def get_admin_identity():
    """Return the admin (reply-capable) sender identity string."""
    name = getattr(settings, "ADMIN_EMAIL_NAME", "Portfolio Admin")
    email = getattr(settings, "ADMIN_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    return f"{name} <{email}>"


# ---------------------------------------------------------------------------
# HTML → plain text strip (lightweight, no extra dependency)
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = StringIO()

    def handle_data(self, data):
        self._text.write(data)

    def get_text(self):
        return self._text.getvalue()


def strip_html(html):
    """Strip HTML tags and return plain text."""
    stripper = _HTMLStripper()
    stripper.feed(html)
    text = stripper.get_text()
    # Collapse multiple blank lines
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------
# Template rendering (uses Django template engine — {{ var }} syntax)
# ---------------------------------------------------------------------------

def _render_string(template_string, context):
    """Render a Django template string with the given context."""
    tpl = Template(template_string)
    return tpl.render(Context(context, autoescape=False))


def render_template(template_name, context):
    """Render an EmailTemplate from the database.

    Returns (subject, html_body, text_body) tuple.
    Falls back to hardcoded defaults if template is missing or inactive.
    Templates use Django template syntax: {{ variable }}
    """
    from .models import EmailTemplate

    defaults = _get_defaults()
    try:
        tpl = EmailTemplate.objects.get(name=template_name, is_active=True)
    except EmailTemplate.DoesNotExist:
        tpl = None

    if tpl:
        subject_tpl = tpl.subject
        html_tpl = tpl.html_body
        text_tpl = tpl.text_body
    else:
        fallback = defaults.get(template_name, {})
        subject_tpl = fallback.get("subject", "{{ subject }}")
        html_tpl = fallback.get("html_body", "<p>{{ content }}</p>")
        text_tpl = fallback.get("text_body", "")

    subject = _render_string(subject_tpl, context)
    html_body = _render_string(html_tpl, context)
    text_body = _render_string(text_tpl, context) if text_tpl else strip_html(html_body)

    return subject, html_body, text_body


# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------

def send_html_email(subject, html_body, text_body, from_identity, to_email):
    """Send an HTML email with plain text fallback using EmailMultiAlternatives."""
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_identity,
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


# ---------------------------------------------------------------------------
# Default HTML templates (uses Django template syntax: {{ variable }})
# ---------------------------------------------------------------------------

BASE_HTML_WRAPPER = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s</title>
<style>
  body { margin: 0; padding: 0; background-color: #f4f4f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
  .email-wrapper { width: 100%%; background-color: #f4f4f7; padding: 40px 0; }
  .email-container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .email-header { background-color: #1e3a5f; color: #ffffff; padding: 24px 32px; text-align: center; }
  .email-header h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }
  .email-body { padding: 32px; color: #333333; line-height: 1.6; font-size: 15px; }
  .email-body h2 { margin-top: 0; color: #1e3a5f; font-size: 18px; }
  .email-body p { margin: 0 0 16px; }
  .email-body .meta { color: #666666; font-size: 13px; border-left: 3px solid #3b82f6; padding-left: 12px; margin-bottom: 20px; }
  .email-body .content { background-color: #f8fafc; border-radius: 6px; padding: 20px; margin: 16px 0; }
  .email-footer { padding: 20px 32px; text-align: center; color: #999999; font-size: 12px; border-top: 1px solid #eeeeee; }
</style>
</head>
<body>
<div class="email-wrapper">
  <div class="email-container">
    <div class="email-header">
      <h1>%(header_title)s</h1>
    </div>
    <div class="email-body">
      %(body_content)s
    </div>
    <div class="email-footer">
      %(footer_text)s
    </div>
  </div>
</div>
</body>
</html>"""


def _get_defaults():
    """Return default template definitions used for seeding and fallback.

    All templates use Django template syntax ({{ variable }}) so CSS curly
    braces don't conflict with placeholder rendering.
    """
    contact_html = BASE_HTML_WRAPPER % {
        "title": "New contact message: {{ subject }}",
        "header_title": "New Contact Message",
        "body_content": (
            '<h2>{{ subject }}</h2>'
            '<div class="meta">'
            '<strong>From:</strong> {{ name }} &lt;{{ email }}&gt;'
            '</div>'
            '<div class="content">'
            '<p>{{ message }}</p>'
            '</div>'
        ),
        "footer_text": "This is an automated notification from your portfolio website.",
    }

    reply_html = BASE_HTML_WRAPPER % {
        "title": "Re: {{ subject }}",
        "header_title": "Message from Portfolio Admin",
        "body_content": (
            '<h2>Re: {{ subject }}</h2>'
            '<div class="content">'
            '<p>{{ reply_body }}</p>'
            '</div>'
            '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
            '<p style="color:#888;font-size:13px;">'
            '<strong>Your original message:</strong><br>{{ original_message }}'
            '</p>'
        ),
        "footer_text": "You are receiving this because you contacted us via our portfolio website.",
    }

    new_email_html = BASE_HTML_WRAPPER % {
        "title": "{{ subject }}",
        "header_title": "Message from Portfolio Admin",
        "body_content": (
            '<h2>{{ subject }}</h2>'
            '<div class="content">'
            '<p>{{ body }}</p>'
            '</div>'
        ),
        "footer_text": "This email was sent from the portfolio admin panel.",
    }

    return {
        "contact_notification": {
            "subject": "New contact message: {{ subject }}",
            "html_body": contact_html,
            "text_body": (
                "New contact message\n"
                "---\n"
                "From: {{ name }} <{{ email }}>\n"
                "Subject: {{ subject }}\n\n"
                "{{ message }}"
            ),
        },
        "admin_reply": {
            "subject": "Re: {{ subject }}",
            "html_body": reply_html,
            "text_body": (
                "Re: {{ subject }}\n\n"
                "{{ reply_body }}\n\n"
                "---\n"
                "Your original message:\n"
                "{{ original_message }}"
            ),
        },
        "admin_new_email": {
            "subject": "{{ subject }}",
            "html_body": new_email_html,
            "text_body": "{{ subject }}\n\n{{ body }}",
        },
    }
