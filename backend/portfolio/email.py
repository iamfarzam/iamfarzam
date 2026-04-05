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


def _get_branding():
    """Pull branding from the Profile singleton. Returns a dict of brand variables."""
    from .models import Profile

    try:
        profile = Profile.objects.first()
    except Exception:
        profile = None

    if profile:
        return {
            "brand_name": profile.full_name,
            "brand_email": profile.email,
            "brand_website": profile.website_url or "",
            "brand_github": profile.github_url or "",
            "brand_linkedin": profile.linkedin_url or "",
        }
    return {
        "brand_name": getattr(settings, "SYSTEM_EMAIL_NAME", "Portfolio"),
        "brand_email": settings.DEFAULT_FROM_EMAIL,
        "brand_website": "",
        "brand_github": "",
        "brand_linkedin": "",
    }


def render_template(template_name, context):
    """Render an EmailTemplate from the database.

    Returns (subject, html_body, text_body) tuple.
    Falls back to hardcoded defaults if template is missing or inactive.
    Templates use Django template syntax: {{ variable }}
    Branding variables from the Profile model are automatically injected.
    """
    from .models import EmailTemplate

    # Inject branding into context (template-provided values take priority)
    full_context = _get_branding()
    full_context.update(context)

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

    subject = _render_string(subject_tpl, full_context)
    html_body = _render_string(html_tpl, full_context)
    text_body = _render_string(text_tpl, full_context) if text_tpl else strip_html(html_body)

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
#
# Professional table-based layout with fully inlined styles for maximum
# email client compatibility (Gmail, Outlook, Apple Mail, Yahoo, etc.).
# ---------------------------------------------------------------------------

# Table-based, fully-inlined HTML email wrapper.
# Uses %%(variable)s for Django template placeholders and %(variable)s
# for Python string interpolation of structural parts.
BASE_HTML_WRAPPER = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light dark" />
  <meta name="supported-color-schemes" content="light dark" />
  <title>%(title)s</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
  <style type="text/css">
    /* Reset */
    body, table, td, p, a, li, blockquote { -webkit-text-size-adjust: 100%%; -ms-text-size-adjust: 100%%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }
    body { margin: 0 !important; padding: 0 !important; width: 100%% !important; }
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
      .email-bg { background-color: #1a1a2e !important; }
      .email-card { background-color: #16213e !important; }
      .email-body-text { color: #e0e0e0 !important; }
      .email-heading { color: #90caf9 !important; }
      .email-meta { color: #b0b0b0 !important; }
      .email-content-block { background-color: #1a1a2e !important; }
      .email-footer-text { color: #777777 !important; }
      .email-divider { border-color: #2a2a4a !important; }
    }
    /* Responsive */
    @media only screen and (max-width: 620px) {
      .email-container { width: 100%% !important; max-width: 100%% !important; }
      .email-padding { padding: 24px 20px !important; }
      .email-header-padding { padding: 20px !important; }
    }
  </style>
</head>
<body style="margin:0;padding:0;word-spacing:normal;background-color:#f0f2f5;">
  <!-- Preheader (hidden preview text) -->
  <div style="display:none;font-size:1px;color:#f0f2f5;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    %(preheader)s
  </div>

  <!-- Email wrapper table -->
  <table role="presentation" class="email-bg" style="width:100%%;border:none;border-spacing:0;background-color:#f0f2f5;" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 10px;">

        <!-- Main container -->
        <table role="presentation" class="email-container" style="width:600px;max-width:600px;border:none;border-spacing:0;text-align:left;" cellpadding="0" cellspacing="0">

          <!-- Header -->
          <tr>
            <td class="email-header-padding" style="padding:32px 40px;background-color:#1e3a5f;text-align:center;border-radius:8px 8px 0 0;">
              <h1 style="margin:0;font-size:22px;font-weight:700;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#ffffff;letter-spacing:0.3px;">
                %(header_title)s
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td class="email-card email-padding" style="padding:36px 40px;background-color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.7;color:#333333;">
              %(body_content)s
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td class="email-card email-padding" style="padding:20px 40px;background-color:#ffffff;border-top:1px solid #e8e8e8;text-align:center;border-radius:0 0 8px 8px;">
              <p class="email-footer-text" style="margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#999999;">
                %(footer_text)s
              </p>
            </td>
          </tr>

        </table>
        <!-- /Main container -->

      </td>
    </tr>
  </table>
  <!-- /Email wrapper -->
</body>
</html>"""


def _get_defaults():
    """Return default template definitions used for seeding and fallback.

    All templates use Django template syntax ({{ variable }}) so CSS curly
    braces don't conflict with placeholder rendering.

    Branding variables (auto-injected from Profile):
      {{ brand_name }}, {{ brand_email }}, {{ brand_website }},
      {{ brand_github }}, {{ brand_linkedin }}
    """
    contact_html = BASE_HTML_WRAPPER % {
        "title": "New contact message: {{ subject }}",
        "preheader": "New message from {{ name }} regarding &quot;{{ subject }}&quot;",
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<!-- Greeting -->'
            '<p class="email-body-text" style="margin:0 0 8px;font-size:15px;line-height:1.7;color:#333333;">'
            'You have received a new inquiry through your portfolio contact form.'
            '</p>'

            '<!-- Subject heading -->'
            '<h2 class="email-heading" style="margin:20px 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            '{{ subject }}'
            '</h2>'

            '<!-- Sender details -->'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:24px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td style="padding:14px 18px;background-color:#f8fafc;border-left:4px solid #3b82f6;border-radius:0 6px 6px 0;">'
            '<p class="email-meta" style="margin:0 0 4px;font-size:14px;line-height:1.5;color:#333333;font-weight:600;">{{ name }}</p>'
            '<p class="email-meta" style="margin:0;font-size:13px;line-height:1.5;color:#666666;">'
            '<a href="mailto:{{ email }}" style="color:#3b82f6;text-decoration:none;">{{ email }}</a>'
            '</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<!-- Message content -->'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:24px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ message }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<!-- Action hint -->'
            '<p class="email-meta" style="margin:0;font-size:13px;line-height:1.5;color:#888888;">'
            'You can reply to this message directly from the '
            '<a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">admin panel</a>.'
            '</p>'
        ),
        "footer_text": (
            '&copy; {{ brand_name }}'
            '{% if brand_website %}'
            ' &middot; <a href="{{ brand_website }}" style="color:#999999;text-decoration:underline;">{{ brand_website }}</a>'
            '{% endif %}'
            '<br/>This is an automated notification. Please do not reply directly to this email.'
        ),
    }

    reply_html = BASE_HTML_WRAPPER % {
        "title": "Re: {{ subject }}",
        "preheader": "{{ brand_name }} has responded to your inquiry",
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<!-- Greeting -->'
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            'Hello {{ name }},'
            '</p>'
            '<p class="email-body-text" style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#666666;">'
            'Thank you for reaching out. Please find our response below.'
            '</p>'

            '<!-- Reply heading -->'
            '<h2 class="email-heading" style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            'Re: {{ subject }}'
            '</h2>'

            '<!-- Reply body -->'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:28px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ reply_body }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<!-- Divider -->'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:20px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-divider" style="border-top:1px solid #e8e8e8;font-size:0;line-height:0;">&nbsp;</td>'
            '</tr>'
            '</table>'

            '<!-- Original message reference -->'
            '<p class="email-meta" style="margin:0 0 10px;font-size:11px;font-weight:700;color:#999999;text-transform:uppercase;letter-spacing:0.8px;">Your Original Message</p>'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:20px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td style="padding:16px 20px;background-color:#fafafa;border-left:3px solid #d1d5db;border-radius:0 6px 6px 0;">'
            '<p style="margin:0;font-size:13px;line-height:1.6;color:#888888;white-space:pre-wrap;">{{ original_message }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<!-- Sign-off -->'
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            'Best regards,'
            '</p>'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;font-weight:600;">'
            '{{ brand_name }}'
            '</p>'
        ),
        "footer_text": (
            '&copy; {{ brand_name }}'
            '{% if brand_website %}'
            ' &middot; <a href="{{ brand_website }}" style="color:#999999;text-decoration:underline;">{{ brand_website }}</a>'
            '{% endif %}'
            '<br/>You are receiving this email because you submitted an inquiry through our website.'
        ),
    }

    new_email_html = BASE_HTML_WRAPPER % {
        "title": "{{ subject }}",
        "preheader": "A message from {{ brand_name }}",
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<!-- Greeting -->'
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            'Hello{% if name %} {{ name }}{% endif %},'
            '</p>'
            '<p class="email-body-text" style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#666666;">'
            'We hope this message finds you well.'
            '</p>'

            '<!-- Subject heading -->'
            '<h2 class="email-heading" style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            '{{ subject }}'
            '</h2>'

            '<!-- Email body -->'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:24px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ body }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<!-- Sign-off -->'
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            'Best regards,'
            '</p>'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;font-weight:600;">'
            '{{ brand_name }}'
            '</p>'
        ),
        "footer_text": (
            '&copy; {{ brand_name }}'
            '{% if brand_website %}'
            ' &middot; <a href="{{ brand_website }}" style="color:#999999;text-decoration:underline;">{{ brand_website }}</a>'
            '{% endif %}'
            '<br/>This email was sent by {{ brand_name }}.'
        ),
    }

    return {
        "contact_notification": {
            "subject": "[{{ brand_name }}] New inquiry: {{ subject }}",
            "html_body": contact_html,
            "text_body": (
                "New Contact Inquiry\n"
                "========================\n\n"
                "From: {{ name }} <{{ email }}>\n"
                "Subject: {{ subject }}\n\n"
                "Message:\n"
                "{{ message }}\n\n"
                "---\n"
                "Reply via the admin panel.\n"
                "{{ brand_name }}"
            ),
        },
        "admin_reply": {
            "subject": "Re: {{ subject }}",
            "html_body": reply_html,
            "text_body": (
                "Hello {{ name }},\n\n"
                "Thank you for reaching out. Please find our response below.\n\n"
                "Re: {{ subject }}\n"
                "---\n\n"
                "{{ reply_body }}\n\n"
                "---\n"
                "Your original message:\n\n"
                "{{ original_message }}\n\n"
                "Best regards,\n"
                "{{ brand_name }}"
            ),
        },
        "admin_new_email": {
            "subject": "{{ subject }}",
            "html_body": new_email_html,
            "text_body": (
                "Hello{{ name }},\n\n"
                "{{ subject }}\n"
                "---\n\n"
                "{{ body }}\n\n"
                "Best regards,\n"
                "{{ brand_name }}"
            ),
        },
    }
