"""Email rendering and sending — class-based service.

The module exposes a single ``EmailService`` class that owns:
  * sender-identity resolution (system noreply vs. active EmailConfiguration)
  * branding context lookup from the Profile singleton
  * template rendering (with optional language override for modeltranslation)
  * SMTP connection construction from an EmailConfiguration row
  * the actual ``send`` operation

A small ``HTMLStripper`` helper sits next to it for the plain-text fallback.

Module-level ``_get_defaults`` / ``_get_strings`` remain because they are pure
data, called from a data migration that should not be coupled to a service
class.
"""

import logging
import re
from html.parser import HTMLParser
from io import StringIO

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import Context, Template
from django.utils import translation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML → plain text helper
# ---------------------------------------------------------------------------

class HTMLStripper(HTMLParser):
    """Tag stripper used to derive a plain-text fallback from rendered HTML."""

    def __init__(self):
        super().__init__()
        self._text = StringIO()

    def handle_data(self, data):
        self._text.write(data)

    def get_text(self):
        return self._text.getvalue()

    @classmethod
    def to_text(cls, html):
        stripper = cls()
        stripper.feed(html)
        text = stripper.get_text()
        return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------
# EmailService
# ---------------------------------------------------------------------------

class EmailService:
    """Owns sender identity, template rendering, and SMTP send.

    All public methods are classmethods/staticmethods so the service can be
    used without instantiation (no per-call state). The active
    EmailConfiguration row is looked up on each call, so admins can swap
    configs without restarting workers.
    """

    SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    # -- configuration / identity -------------------------------------------

    @staticmethod
    def get_active_config():
        """Return the currently active EmailConfiguration row, or None."""
        from .models import EmailConfiguration

        try:
            return EmailConfiguration.objects.filter(is_active=True).first()
        except Exception:
            logger.exception("Failed to query active EmailConfiguration")
            return None

    @staticmethod
    def get_system_identity():
        """Return the system (noreply) sender identity string."""
        name = getattr(settings, "SYSTEM_EMAIL_NAME", "Portfolio")
        email = settings.DEFAULT_FROM_EMAIL
        return f"{name} <{email}>"

    @classmethod
    def get_admin_identity(cls):
        """Return the admin sender identity. Prefers the active EmailConfiguration."""
        config = cls.get_active_config()
        if config:
            return config.from_identity
        name = getattr(settings, "ADMIN_EMAIL_NAME", "Portfolio Admin")
        email = getattr(settings, "ADMIN_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
        return f"{name} <{email}>"

    @classmethod
    def get_admin_reply_to(cls):
        """Return the Reply-To identity from the active config, or empty string."""
        config = cls.get_active_config()
        return config.reply_to_identity if config else ""

    # -- template rendering -------------------------------------------------

    @staticmethod
    def render_string(template_string, context):
        """Render a Django template string with the given context."""
        return Template(template_string).render(Context(context))

    @staticmethod
    def render_text_string(template_string, context):
        """Render a plain-text template (HTML auto-escape disabled)."""
        wrapped = "{% autoescape off %}" + template_string + "{% endautoescape %}"
        return Template(wrapped).render(Context(context))

    @staticmethod
    def get_branding():
        """Pull branding variables from the Profile singleton."""
        from .models import Profile

        try:
            profile = Profile.objects.first()
        except Exception:
            logger.exception("Failed to load Profile for email branding")
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

    @classmethod
    def render_template(cls, template_name, context, language=None):
        """Render an EmailTemplate row → ``(subject, html_body, text_body)``.

        Falls back to ``_get_defaults`` if no active row exists. When
        ``language`` is supplied, ``translation.override`` is used so
        modeltranslation resolves the right translated column. Missing
        translations fall back through MODELTRANSLATION_FALLBACK_LANGUAGES.
        """
        from .models import EmailTemplate

        full_context = cls.get_branding()
        full_context.update(context)

        try:
            tpl = EmailTemplate.objects.get(name=template_name, is_active=True)
        except EmailTemplate.DoesNotExist:
            tpl = None

        target_language = language or settings.LANGUAGE_CODE
        with translation.override(target_language):
            if tpl:
                subject_tpl = tpl.subject
                html_tpl = tpl.html_body
                text_tpl = tpl.text_body
            else:
                fallback = _get_defaults(target_language).get(template_name, {})
                subject_tpl = fallback.get("subject", "{{ subject }}")
                html_tpl = fallback.get("html_body", "<p>{{ content }}</p>")
                text_tpl = fallback.get("text_body", "")

            subject = cls.render_string(subject_tpl, full_context)
            html_body = cls.render_string(html_tpl, full_context)
            text_body = (
                cls.render_text_string(text_tpl, full_context)
                if text_tpl
                else HTMLStripper.to_text(html_body)
            )

        return subject, html_body, text_body

    # -- transport / send ---------------------------------------------------

    @classmethod
    def build_connection(cls, config):
        """Build a one-off SMTP connection using the given EmailConfiguration."""
        return get_connection(
            backend=cls.SMTP_BACKEND,
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            use_tls=config.use_tls,
            use_ssl=config.use_ssl,
        )

    @classmethod
    def send(
        cls,
        subject,
        html_body,
        text_body,
        from_identity,
        to_email,
        reply_to=None,
        use_active_config=False,
    ):
        """Send an HTML email with a plain-text fallback.

        When ``use_active_config`` is true and an active EmailConfiguration
        row exists, transport, From identity, and Reply-To are taken from
        that row (overriding the supplied values). Otherwise the function
        falls back to Django's project-level email settings.
        """
        connection = None
        reply_to_list = list(reply_to) if reply_to else []

        if use_active_config:
            config = cls.get_active_config()
            if config:
                connection = cls.build_connection(config)
                from_identity = config.from_identity
                if config.reply_to_identity:
                    reply_to_list = [config.reply_to_identity]

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_identity,
            to=[to_email],
            reply_to=reply_to_list or None,
            connection=connection,
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
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light only">
  <title>%(title)s</title>
  <!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
  <style type="text/css">
    body, table, td, p, a, li { -webkit-text-size-adjust:100%%; -ms-text-size-adjust:100%%; }
    table, td { mso-table-lspace:0pt; mso-table-rspace:0pt; border-collapse:collapse; }
    img { -ms-interpolation-mode:bicubic; border:0; outline:none; text-decoration:none; max-width:100%%; height:auto; }
    body { margin:0 !important; padding:0 !important; width:100%% !important; }
    a { color:#0a66c2; }
    @media only screen and (max-width:620px) {
      .container { width:100%% !important; }
      .pad-x { padding-left:24px !important; padding-right:24px !important; }
    }
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f5f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;">
  <div style="display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;color:#f5f6f8;font-size:1px;line-height:1px;">%(preheader)s</div>
  <table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f6f8;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:8px;">
          <tr>
            <td class="pad-x" style="padding:32px 40px 0;">
              <p style="margin:0;font-size:13px;font-weight:600;letter-spacing:-0.01em;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">%(header_title)s</p>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:24px 40px 40px;font-size:16px;line-height:1.6;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              %(body_content)s
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:0 40px;">
              <div style="border-top:1px solid #e5e7eb;height:1px;font-size:0;line-height:0;">&nbsp;</div>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:20px 40px 28px;font-size:12px;line-height:1.6;color:#6b7280;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              %(footer_text)s
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Translated phrases used inside the templates.
#
# The HTML/text scaffolding lives in `_get_defaults` below — only these
# phrases swap per language. Variables in {{ ... }} and {% ... %} are
# Django template syntax and must be preserved exactly when translating.
# ---------------------------------------------------------------------------

TEMPLATE_STRINGS = {
    "en": {
        "contact_subject": "New message from {{ name }}: {{ subject }}",
        "contact_title": "New contact message",
        "contact_preheader": "{{ name }} sent a message about {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Sent automatically when someone uses your contact form.",
        "text_contact_header": "New contact message",
        "text_contact_from": "From",
        "text_contact_subject_label": "Subject",
        "text_contact_message_label": "Message",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} replied to your message.",
        "reply_greeting": "Hi {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "On your original message",
        "reply_signoff": "Best,",
        "reply_footer": "Replying to a message you sent via the contact form.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "A note from {{ brand_name }}.",
        "new_email_greeting": "Hi{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Best,",
        "new_email_footer": "",
    },
    "es": {
        "contact_subject": "Nuevo mensaje de {{ name }}: {{ subject }}",
        "contact_title": "Nuevo mensaje de contacto",
        "contact_preheader": "{{ name }} te envió un mensaje sobre {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Enviado automáticamente cuando alguien usa tu formulario de contacto.",
        "text_contact_header": "Nuevo mensaje de contacto",
        "text_contact_from": "De",
        "text_contact_subject_label": "Asunto",
        "text_contact_message_label": "Mensaje",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} respondió a tu mensaje.",
        "reply_greeting": "Hola {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Sobre tu mensaje original",
        "reply_signoff": "Saludos,",
        "reply_footer": "Respuesta a un mensaje enviado a través del formulario de contacto.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un mensaje de {{ brand_name }}.",
        "new_email_greeting": "Hola{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Saludos,",
        "new_email_footer": "",
    },
    "fr": {
        "contact_subject": "Nouveau message de {{ name }} : {{ subject }}",
        "contact_title": "Nouveau message de contact",
        "contact_preheader": "{{ name }} t'a envoyé un message au sujet de {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Envoyé automatiquement lorsqu'une personne utilise ton formulaire de contact.",
        "text_contact_header": "Nouveau message de contact",
        "text_contact_from": "De",
        "text_contact_subject_label": "Sujet",
        "text_contact_message_label": "Message",
        "text_contact_reply_hint": "",
        "reply_subject": "Re : {{ subject }}",
        "reply_title": "Re : {{ subject }}",
        "reply_preheader": "{{ brand_name }} a répondu à votre message.",
        "reply_greeting": "Bonjour {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Concernant votre message initial",
        "reply_signoff": "Cordialement,",
        "reply_footer": "Réponse à un message envoyé via le formulaire de contact.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un message de {{ brand_name }}.",
        "new_email_greeting": "Bonjour{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Cordialement,",
        "new_email_footer": "",
    },
    "de": {
        "contact_subject": "Neue Nachricht von {{ name }}: {{ subject }}",
        "contact_title": "Neue Kontaktnachricht",
        "contact_preheader": "{{ name }} hat dir eine Nachricht zu {{ subject }} gesendet.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Wird automatisch gesendet, wenn jemand dein Kontaktformular benutzt.",
        "text_contact_header": "Neue Kontaktnachricht",
        "text_contact_from": "Von",
        "text_contact_subject_label": "Betreff",
        "text_contact_message_label": "Nachricht",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} hat auf Ihre Nachricht geantwortet.",
        "reply_greeting": "Hallo {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Zu Ihrer ursprünglichen Nachricht",
        "reply_signoff": "Beste Grüße,",
        "reply_footer": "Antwort auf eine Nachricht, die Sie über das Kontaktformular gesendet haben.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Eine Nachricht von {{ brand_name }}.",
        "new_email_greeting": "Hallo{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Beste Grüße,",
        "new_email_footer": "",
    },
    "zh-hans": {
        "contact_subject": "{{ name }} 的新消息：{{ subject }}",
        "contact_title": "新的联络消息",
        "contact_preheader": "{{ name }} 就 {{ subject }} 给你留言。",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "有人使用您的联络表单时自动发送。",
        "text_contact_header": "新的联络消息",
        "text_contact_from": "来自",
        "text_contact_subject_label": "主题",
        "text_contact_message_label": "消息",
        "text_contact_reply_hint": "",
        "reply_subject": "回复：{{ subject }}",
        "reply_title": "回复：{{ subject }}",
        "reply_preheader": "{{ brand_name }} 已回复您的消息。",
        "reply_greeting": "{{ name }} 您好，",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "关于您原本的消息",
        "reply_signoff": "此致，",
        "reply_footer": "回复您通过联络表单发送的消息。",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} 的留言。",
        "new_email_greeting": "{% if name %}{{ name }} 您好{% else %}您好{% endif %}，",
        "new_email_intro": "",
        "new_email_signoff": "此致，",
        "new_email_footer": "",
    },
    "ja": {
        "contact_subject": "{{ name }} 様から新しいメッセージ：{{ subject }}",
        "contact_title": "新しいお問い合わせ",
        "contact_preheader": "{{ name }} 様より {{ subject }} に関するメッセージが届きました。",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "お問い合わせフォームから送信があった際に自動で送られます。",
        "text_contact_header": "新しいお問い合わせ",
        "text_contact_from": "差出人",
        "text_contact_subject_label": "件名",
        "text_contact_message_label": "本文",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} よりご返信です。",
        "reply_greeting": "{{ name }} 様",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "お送りいただいたメッセージについて",
        "reply_signoff": "よろしくお願いいたします。",
        "reply_footer": "お問い合わせフォームからお送りいただいたメッセージへの返信です。",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} よりご連絡。",
        "new_email_greeting": "{% if name %}{{ name }} 様{% else %}ご担当者様{% endif %}",
        "new_email_intro": "",
        "new_email_signoff": "よろしくお願いいたします。",
        "new_email_footer": "",
    },
    "ar": {
        "contact_subject": "رسالة جديدة من {{ name }}: {{ subject }}",
        "contact_title": "رسالة تواصل جديدة",
        "contact_preheader": "أرسل {{ name }} رسالة بشأن {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "تُرسل تلقائياً عندما يستخدم شخص ما نموذج التواصل.",
        "text_contact_header": "رسالة تواصل جديدة",
        "text_contact_from": "من",
        "text_contact_subject_label": "الموضوع",
        "text_contact_message_label": "الرسالة",
        "text_contact_reply_hint": "",
        "reply_subject": "رد: {{ subject }}",
        "reply_title": "رد: {{ subject }}",
        "reply_preheader": "ردّ {{ brand_name }} على رسالتك.",
        "reply_greeting": "مرحباً {{ name }}،",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "بخصوص رسالتك الأصلية",
        "reply_signoff": "تحياتي،",
        "reply_footer": "ردّ على رسالة أرسلتها عبر نموذج التواصل.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "رسالة من {{ brand_name }}.",
        "new_email_greeting": "مرحباً{% if name %} {{ name }}{% endif %}،",
        "new_email_intro": "",
        "new_email_signoff": "تحياتي،",
        "new_email_footer": "",
    },
    "pt": {
        "contact_subject": "Nova mensagem de {{ name }}: {{ subject }}",
        "contact_title": "Nova mensagem de contato",
        "contact_preheader": "{{ name }} te enviou uma mensagem sobre {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Enviado automaticamente quando alguém usa o seu formulário de contato.",
        "text_contact_header": "Nova mensagem de contato",
        "text_contact_from": "De",
        "text_contact_subject_label": "Assunto",
        "text_contact_message_label": "Mensagem",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} respondeu à sua mensagem.",
        "reply_greeting": "Olá {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Sobre a sua mensagem original",
        "reply_signoff": "Atenciosamente,",
        "reply_footer": "Resposta a uma mensagem enviada pelo formulário de contato.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Uma mensagem de {{ brand_name }}.",
        "new_email_greeting": "Olá{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Atenciosamente,",
        "new_email_footer": "",
    },
    "ru": {
        "contact_subject": "Новое сообщение от {{ name }}: {{ subject }}",
        "contact_title": "Новое сообщение из формы связи",
        "contact_preheader": "{{ name }} прислал(а) сообщение о {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Отправляется автоматически, когда кто-то пишет через вашу форму связи.",
        "text_contact_header": "Новое сообщение из формы связи",
        "text_contact_from": "От",
        "text_contact_subject_label": "Тема",
        "text_contact_message_label": "Сообщение",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ответил(а) на ваше сообщение.",
        "reply_greeting": "Здравствуйте, {{ name }}!",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "По вашему изначальному сообщению",
        "reply_signoff": "С уважением,",
        "reply_footer": "Ответ на сообщение, отправленное через форму связи.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Сообщение от {{ brand_name }}.",
        "new_email_greeting": "Здравствуйте{% if name %}, {{ name }}{% endif %}!",
        "new_email_intro": "",
        "new_email_signoff": "С уважением,",
        "new_email_footer": "",
    },
    "bn": {
        "contact_subject": "{{ name }} থেকে নতুন বার্তা: {{ subject }}",
        "contact_title": "নতুন যোগাযোগ-বার্তা",
        "contact_preheader": "{{ name }} আপনাকে {{ subject }} বিষয়ে বার্তা পাঠিয়েছেন।",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "কেউ আপনার যোগাযোগ-ফর্ম ব্যবহার করলে স্বয়ংক্রিয়ভাবে পাঠানো হয়।",
        "text_contact_header": "নতুন যোগাযোগ-বার্তা",
        "text_contact_from": "প্রেরক",
        "text_contact_subject_label": "বিষয়",
        "text_contact_message_label": "বার্তা",
        "text_contact_reply_hint": "",
        "reply_subject": "উত্তর: {{ subject }}",
        "reply_title": "উত্তর: {{ subject }}",
        "reply_preheader": "{{ brand_name }} আপনার বার্তার উত্তর দিয়েছেন।",
        "reply_greeting": "নমস্কার {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "আপনার মূল বার্তা সম্পর্কে",
        "reply_signoff": "শুভেচ্ছান্তে,",
        "reply_footer": "যোগাযোগ-ফর্মের মাধ্যমে পাঠানো বার্তার উত্তর।",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} থেকে একটি বার্তা।",
        "new_email_greeting": "নমস্কার{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "শুভেচ্ছান্তে,",
        "new_email_footer": "",
    },
    "hi": {
        "contact_subject": "{{ name }} से नया संदेश: {{ subject }}",
        "contact_title": "नया संपर्क संदेश",
        "contact_preheader": "{{ name }} ने {{ subject }} के बारे में आपको संदेश भेजा।",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "जब कोई आपका संपर्क फ़ॉर्म इस्तेमाल करता है तब स्वतः भेजा जाता है।",
        "text_contact_header": "नया संपर्क संदेश",
        "text_contact_from": "प्रेषक",
        "text_contact_subject_label": "विषय",
        "text_contact_message_label": "संदेश",
        "text_contact_reply_hint": "",
        "reply_subject": "उत्तर: {{ subject }}",
        "reply_title": "उत्तर: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ने आपके संदेश का उत्तर दिया।",
        "reply_greeting": "नमस्ते {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "आपके मूल संदेश के बारे में",
        "reply_signoff": "सादर,",
        "reply_footer": "संपर्क फ़ॉर्म से भेजे गए संदेश का उत्तर।",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} की ओर से एक नोट।",
        "new_email_greeting": "नमस्ते{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "सादर,",
        "new_email_footer": "",
    },
    "ur": {
        "contact_subject": "{{ name }} کی طرف سے نیا پیغام: {{ subject }}",
        "contact_title": "نیا رابطہ پیغام",
        "contact_preheader": "{{ name }} نے {{ subject }} کے بارے میں آپ کو پیغام بھیجا۔",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "جب کوئی آپ کا رابطہ فارم استعمال کرتا ہے تو خودکار طور پر بھیجا جاتا ہے۔",
        "text_contact_header": "نیا رابطہ پیغام",
        "text_contact_from": "بھیجنے والا",
        "text_contact_subject_label": "موضوع",
        "text_contact_message_label": "پیغام",
        "text_contact_reply_hint": "",
        "reply_subject": "جواب: {{ subject }}",
        "reply_title": "جواب: {{ subject }}",
        "reply_preheader": "{{ brand_name }} نے آپ کے پیغام کا جواب دیا۔",
        "reply_greeting": "السلام علیکم {{ name }}،",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "آپ کے اصل پیغام کے بارے میں",
        "reply_signoff": "والسلام،",
        "reply_footer": "رابطہ فارم کے ذریعے بھیجے گئے پیغام کا جواب۔",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} کی طرف سے ایک نوٹ۔",
        "new_email_greeting": "السلام علیکم{% if name %} {{ name }}{% endif %}،",
        "new_email_intro": "",
        "new_email_signoff": "والسلام،",
        "new_email_footer": "",
    },
    "ko": {
        "contact_subject": "{{ name }} 님이 보낸 새 메시지: {{ subject }}",
        "contact_title": "새 문의 메시지",
        "contact_preheader": "{{ name }} 님이 {{ subject }} 관련 메시지를 보냈습니다.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "누군가 문의 양식을 사용하면 자동으로 발송됩니다.",
        "text_contact_header": "새 문의 메시지",
        "text_contact_from": "보낸 사람",
        "text_contact_subject_label": "제목",
        "text_contact_message_label": "메시지",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} 님이 메시지에 답장했습니다.",
        "reply_greeting": "{{ name }} 님께,",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "원래 메시지에 관하여",
        "reply_signoff": "감사합니다,",
        "reply_footer": "문의 양식으로 보내주신 메시지에 대한 답장입니다.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} 님이 보낸 메모.",
        "new_email_greeting": "{% if name %}{{ name }} 님께{% else %}안녕하세요{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "감사합니다,",
        "new_email_footer": "",
    },
    "tr": {
        "contact_subject": "{{ name }} adlı kişiden yeni mesaj: {{ subject }}",
        "contact_title": "Yeni iletişim mesajı",
        "contact_preheader": "{{ name }}, {{ subject }} hakkında size mesaj gönderdi.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Birisi iletişim formunuzu kullandığında otomatik olarak gönderilir.",
        "text_contact_header": "Yeni iletişim mesajı",
        "text_contact_from": "Gönderen",
        "text_contact_subject_label": "Konu",
        "text_contact_message_label": "Mesaj",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} mesajınıza yanıt verdi.",
        "reply_greeting": "Merhaba {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Özgün mesajınız hakkında",
        "reply_signoff": "Saygılarımla,",
        "reply_footer": "İletişim formu üzerinden gönderdiğiniz bir mesaja yanıt.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} tarafından bir not.",
        "new_email_greeting": "Merhaba{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Saygılarımla,",
        "new_email_footer": "",
    },
    "ro": {
        "contact_subject": "Mesaj nou de la {{ name }}: {{ subject }}",
        "contact_title": "Mesaj nou de contact",
        "contact_preheader": "{{ name }} ți-a trimis un mesaj despre {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Trimis automat când cineva folosește formularul tău de contact.",
        "text_contact_header": "Mesaj nou de contact",
        "text_contact_from": "De la",
        "text_contact_subject_label": "Subiect",
        "text_contact_message_label": "Mesaj",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} a răspuns la mesajul tău.",
        "reply_greeting": "Salut {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Despre mesajul tău inițial",
        "reply_signoff": "Cu stimă,",
        "reply_footer": "Răspuns la un mesaj trimis prin formularul de contact.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un mesaj de la {{ brand_name }}.",
        "new_email_greeting": "Salut{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Cu stimă,",
        "new_email_footer": "",
    },
    "hu": {
        "contact_subject": "Új üzenet {{ name }}-tól: {{ subject }}",
        "contact_title": "Új kapcsolatfelvételi üzenet",
        "contact_preheader": "{{ name }} üzenetet küldött a következőről: {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Automatikusan elküldve, ha valaki kitölti a kapcsolatfelvételi űrlapodat.",
        "text_contact_header": "Új kapcsolatfelvételi üzenet",
        "text_contact_from": "Feladó",
        "text_contact_subject_label": "Tárgy",
        "text_contact_message_label": "Üzenet",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} válaszolt az üzenetére.",
        "reply_greeting": "Üdvözlöm, {{ name }}!",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Az eredeti üzenetére vonatkozóan",
        "reply_signoff": "Üdvözlettel,",
        "reply_footer": "Válasz a kapcsolatfelvételi űrlapon keresztül küldött üzenetre.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Üzenet {{ brand_name }}-tól.",
        "new_email_greeting": "Üdvözlöm{% if name %}, {{ name }}{% endif %}!",
        "new_email_intro": "",
        "new_email_signoff": "Üdvözlettel,",
        "new_email_footer": "",
    },
    "it": {
        "contact_subject": "Nuovo messaggio da {{ name }}: {{ subject }}",
        "contact_title": "Nuovo messaggio di contatto",
        "contact_preheader": "{{ name }} ti ha scritto a proposito di {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Inviato automaticamente quando qualcuno usa il tuo modulo di contatto.",
        "text_contact_header": "Nuovo messaggio di contatto",
        "text_contact_from": "Da",
        "text_contact_subject_label": "Oggetto",
        "text_contact_message_label": "Messaggio",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ha risposto al tuo messaggio.",
        "reply_greeting": "Ciao {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Sul tuo messaggio originale",
        "reply_signoff": "A presto,",
        "reply_footer": "Risposta a un messaggio inviato tramite il modulo di contatto.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un messaggio da {{ brand_name }}.",
        "new_email_greeting": "Ciao{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "A presto,",
        "new_email_footer": "",
    },
    "sm": {
        "contact_subject": "Feʻau fou mai ia {{ name }}: {{ subject }}",
        "contact_title": "Feʻau fou mai i le faʻafesoʻotaʻiga",
        "contact_preheader": "Ua auina mai e {{ name }} se feʻau e uiga ia {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "E auina otometi atu pe a faʻaaogā e se tasi lau pepa faʻafesoʻotaʻi.",
        "text_contact_header": "Feʻau fou mai i le faʻafesoʻotaʻiga",
        "text_contact_from": "Mai ia",
        "text_contact_subject_label": "Mataʻupu",
        "text_contact_message_label": "Feʻau",
        "text_contact_reply_hint": "",
        "reply_subject": "Tali: {{ subject }}",
        "reply_title": "Tali: {{ subject }}",
        "reply_preheader": "Ua taliina e {{ brand_name }} lau feʻau.",
        "reply_greeting": "Talofa {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "E uiga i lau uluai feʻau",
        "reply_signoff": "Faʻafetai,",
        "reply_footer": "Tali atu i se feʻau na e auina mai e ala i le pepa faʻafesoʻotaʻi.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "O se feʻau mai ia {{ brand_name }}.",
        "new_email_greeting": "Talofa{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Faʻafetai,",
        "new_email_footer": "",
    },
    "mi": {
        "contact_subject": "Karere hou nā {{ name }}: {{ subject }}",
        "contact_title": "Karere whakapā hou",
        "contact_preheader": "I tukuna e {{ name }} he karere mō {{ subject }}.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "Tukuna aunoatia inā whakamahia e tētahi tō puka whakapā.",
        "text_contact_header": "Karere whakapā hou",
        "text_contact_from": "Nā",
        "text_contact_subject_label": "Kaupapa",
        "text_contact_message_label": "Karere",
        "text_contact_reply_hint": "",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "Kua whakahoki a {{ brand_name }} ki tō karere.",
        "reply_greeting": "Tēnā koe {{ name }},",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "Mō tō karere taketake",
        "reply_signoff": "Ngā mihi,",
        "reply_footer": "He whakahoki ki te karere i tukuna e koe mā te puka whakapā.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "He karere nā {{ brand_name }}.",
        "new_email_greeting": "Tēnā koe{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "",
        "new_email_signoff": "Ngā mihi,",
        "new_email_footer": "",
    },
    "fa": {
        "contact_subject": "پیام تازه از {{ name }}: {{ subject }}",
        "contact_title": "پیام تماس تازه",
        "contact_preheader": "{{ name }} دربارهٔ {{ subject }} برایتان پیام فرستاد.",
        "contact_body_intro": "",
        "contact_action_html": "",
        "contact_footer": "هنگامی که کسی از فرم تماس استفاده می‌کند، خودکار ارسال می‌شود.",
        "text_contact_header": "پیام تماس تازه",
        "text_contact_from": "از",
        "text_contact_subject_label": "موضوع",
        "text_contact_message_label": "پیام",
        "text_contact_reply_hint": "",
        "reply_subject": "پاسخ: {{ subject }}",
        "reply_title": "پاسخ: {{ subject }}",
        "reply_preheader": "{{ brand_name }} به پیام شما پاسخ داد.",
        "reply_greeting": "سلام {{ name }} عزیز،",
        "reply_intro": "",
        "reply_heading": "",
        "reply_original_label": "دربارهٔ پیام اصلی شما",
        "reply_signoff": "با احترام،",
        "reply_footer": "پاسخ به پیامی که از طریق فرم تماس فرستاده‌اید.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "یادداشتی از {{ brand_name }}.",
        "new_email_greeting": "سلام{% if name %} {{ name }}{% endif %}،",
        "new_email_intro": "",
        "new_email_signoff": "با احترام،",
        "new_email_footer": "",
    },
}


def _get_strings(language):
    """Return the phrase map for a language, falling back to English."""
    return TEMPLATE_STRINGS.get(language) or TEMPLATE_STRINGS["en"]


def _get_defaults(language="en"):
    """Return default template definitions for the given language.

    All templates use Django template syntax ({{ variable }}) so CSS curly
    braces don't conflict with placeholder rendering.

    Branding variables (auto-injected from Profile):
      {{ brand_name }}, {{ brand_email }}, {{ brand_website }},
      {{ brand_github }}, {{ brand_linkedin }}
    """
    s = _get_strings(language)

    # Common style constants for the minimalist letter layout.
    LABEL = (
        'font-size:11px;font-weight:600;color:#6b7280;'
        'letter-spacing:0.06em;text-transform:uppercase;'
    )
    TEXT = 'font-size:16px;line-height:1.6;color:#111827;'
    META = 'font-size:13px;line-height:1.6;color:#6b7280;'
    QUOTE = 'border-left:2px solid #e5e7eb;padding:2px 0 2px 16px;white-space:pre-wrap;'

    def _para(text, style=TEXT, mt=0, mb=16):
        if not text:
            return ""
        return (
            f'<p style="margin:{mt}px 0 {mb}px;{style}">'
            f'{text}'
            f'</p>'
        )

    def _meta_row(label, value):
        return (
            '<tr>'
            f'<td style="padding:0 12px 8px 0;{LABEL}vertical-align:top;width:84px;white-space:nowrap;">'
            f'{label}'
            '</td>'
            f'<td style="padding:0 0 8px;{TEXT}vertical-align:top;">'
            f'{value}'
            '</td>'
            '</tr>'
        )

    def _footer_text(extra):
        link = (
            '{% if brand_website %}'
            ' &middot; <a href="{{ brand_website }}" '
            'style="color:#6b7280;text-decoration:underline;">'
            '{{ brand_website }}</a>'
            '{% endif %}'
        )
        brand_line = '{{ brand_name }}' + link
        if not extra:
            return brand_line
        return brand_line + '<br/>' + extra

    contact_html = BASE_HTML_WRAPPER % {
        "title": s["contact_title"],
        "preheader": s["contact_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            _para(s["contact_body_intro"], style=META, mb=20)
            + '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" '
              'style="margin:0 0 24px;border-collapse:collapse;">'
            + _meta_row(s["text_contact_from"], "{{ name }}")
            + _meta_row(
                "Email",
                '<a href="mailto:{{ email }}" '
                'style="color:#0a66c2;text-decoration:none;">{{ email }}</a>',
            )
            + _meta_row(s["text_contact_subject_label"], "{{ subject }}")
            + '</table>'
            + f'<div style="{QUOTE}{TEXT}">{{{{ message }}}}</div>'
            + _para(s["contact_action_html"], style=META, mt=24)
        ),
        "footer_text": _footer_text(s["contact_footer"]),
    }

    reply_html = BASE_HTML_WRAPPER % {
        "title": s["reply_title"],
        "preheader": s["reply_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            _para(s["reply_greeting"])
            + _para(s["reply_intro"], style=META, mb=16)
            + (f'<h2 style="margin:0 0 16px;font-size:18px;font-weight:600;color:#111827;">'
               f'{s["reply_heading"]}</h2>' if s["reply_heading"] else "")
            + f'<div style="margin:0 0 24px;{TEXT}white-space:pre-wrap;">{{{{ reply_body }}}}</div>'
            + f'<p style="margin:0;{TEXT}">{s["reply_signoff"]}<br/>'
              '<span style="font-weight:600;">{{ brand_name }}</span></p>'
            + '<div style="margin:32px 0 0;padding:20px 0 0;border-top:1px solid #e5e7eb;">'
            + f'<p style="margin:0 0 10px;{LABEL}">{s["reply_original_label"]}</p>'
            + f'<div style="{QUOTE}{META}">{{{{ original_message }}}}</div>'
            + '</div>'
        ),
        "footer_text": _footer_text(s["reply_footer"]),
    }

    new_email_html = BASE_HTML_WRAPPER % {
        "title": s["new_email_title"],
        "preheader": s["new_email_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            _para(s["new_email_greeting"])
            + _para(s["new_email_intro"], style=META, mb=16)
            + f'<div style="margin:0 0 24px;{TEXT}white-space:pre-wrap;">{{{{ body }}}}</div>'
            + f'<p style="margin:0;{TEXT}">{s["new_email_signoff"]}<br/>'
              '<span style="font-weight:600;">{{ brand_name }}</span></p>'
        ),
        "footer_text": _footer_text(s["new_email_footer"]),
    }

    def _join(*lines):
        """Join non-empty lines with single newlines, then collapse runs of 3+
        newlines into exactly two so empty phrases don't leave visible gaps."""
        import re as _re

        out = "\n".join(line for line in lines if line is not None)
        return _re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"

    contact_text = _join(
        s["text_contact_header"],
        "=" * len(s["text_contact_header"]),
        "",
        f"{s['text_contact_from']}: {{{{ name }}}} <{{{{ email }}}}>",
        f"{s['text_contact_subject_label']}: {{{{ subject }}}}",
        "",
        f"{s['text_contact_message_label']}:",
        "{{ message }}",
        "",
        "---" if s["text_contact_reply_hint"] else "",
        s["text_contact_reply_hint"] or None,
        "{{ brand_name }}",
    )

    reply_text = _join(
        s["reply_greeting"],
        "",
        s["reply_intro"] or None,
        "",
        "{{ reply_body }}",
        "",
        f"{s['reply_signoff']}",
        "{{ brand_name }}",
        "",
        "---",
        f"{s['reply_original_label']}:",
        "",
        "{{ original_message }}",
    )

    new_email_text = _join(
        s["new_email_greeting"],
        "",
        s["new_email_intro"] or None,
        "",
        "{{ body }}",
        "",
        f"{s['new_email_signoff']}",
        "{{ brand_name }}",
    )

    return {
        "contact_notification": {
            "subject": s["contact_subject"],
            "html_body": contact_html,
            "text_body": contact_text,
        },
        "admin_reply": {
            "subject": s["reply_subject"],
            "html_body": reply_html,
            "text_body": reply_text,
        },
        "admin_new_email": {
            "subject": s["new_email_subject"],
            "html_body": new_email_html,
            "text_body": new_email_text,
        },
    }
