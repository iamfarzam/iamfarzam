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
        return Template(template_string).render(Context(context, autoescape=False))

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
                cls.render_string(text_tpl, full_context)
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


# ---------------------------------------------------------------------------
# Translated phrases used inside the templates.
#
# The HTML/text scaffolding lives in `_get_defaults` below — only these
# phrases swap per language. Variables in {{ ... }} and {% ... %} are
# Django template syntax and must be preserved exactly when translating.
# ---------------------------------------------------------------------------

TEMPLATE_STRINGS = {
    "en": {
        "contact_subject": "[{{ brand_name }}] New inquiry: {{ subject }}",
        "contact_title": "New contact message: {{ subject }}",
        "contact_preheader": "New message from {{ name }} regarding &quot;{{ subject }}&quot;",
        "contact_body_intro": "You have received a new inquiry through your portfolio contact form.",
        "contact_action_html": 'You can reply to this message directly from the <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">admin panel</a>.',
        "contact_footer": "This is an automated notification. Please do not reply directly to this email.",
        "text_contact_header": "New Contact Inquiry",
        "text_contact_from": "From",
        "text_contact_subject_label": "Subject",
        "text_contact_message_label": "Message",
        "text_contact_reply_hint": "Reply via the admin panel.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} has responded to your inquiry",
        "reply_greeting": "Hello {{ name }},",
        "reply_intro": "Thank you for reaching out. Please find our response below.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "Your Original Message",
        "reply_signoff": "Best regards,",
        "reply_footer": "You are receiving this email because you submitted an inquiry through our website.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "A message from {{ brand_name }}",
        "new_email_greeting": "Hello{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "We hope this message finds you well.",
        "new_email_signoff": "Best regards,",
        "new_email_footer": "This email was sent by {{ brand_name }}.",
    },
    "es": {
        "contact_subject": "[{{ brand_name }}] Nueva consulta: {{ subject }}",
        "contact_title": "Nuevo mensaje de contacto: {{ subject }}",
        "contact_preheader": "Nuevo mensaje de {{ name }} sobre &quot;{{ subject }}&quot;",
        "contact_body_intro": "Has recibido una nueva consulta a través del formulario de contacto de tu portafolio.",
        "contact_action_html": 'Puedes responder a este mensaje directamente desde el <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">panel de administración</a>.',
        "contact_footer": "Esta es una notificación automática. Por favor, no responda directamente a este correo.",
        "text_contact_header": "Nueva consulta de contacto",
        "text_contact_from": "De",
        "text_contact_subject_label": "Asunto",
        "text_contact_message_label": "Mensaje",
        "text_contact_reply_hint": "Responda desde el panel de administración.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ha respondido a su consulta",
        "reply_greeting": "Hola {{ name }},",
        "reply_intro": "Gracias por ponerse en contacto. A continuación encontrará nuestra respuesta.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "Su mensaje original",
        "reply_signoff": "Atentamente,",
        "reply_footer": "Recibe este correo porque envió una consulta a través de nuestro sitio web.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un mensaje de {{ brand_name }}",
        "new_email_greeting": "Hola{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Esperamos que este mensaje le encuentre bien.",
        "new_email_signoff": "Atentamente,",
        "new_email_footer": "Este correo ha sido enviado por {{ brand_name }}.",
    },
    "fr": {
        "contact_subject": "[{{ brand_name }}] Nouvelle demande : {{ subject }}",
        "contact_title": "Nouveau message de contact : {{ subject }}",
        "contact_preheader": "Nouveau message de {{ name }} concernant &laquo; {{ subject }} &raquo;",
        "contact_body_intro": "Vous avez reçu une nouvelle demande via le formulaire de contact de votre portfolio.",
        "contact_action_html": 'Vous pouvez répondre à ce message directement depuis le <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">panneau d\'administration</a>.',
        "contact_footer": "Ceci est une notification automatique. Veuillez ne pas répondre directement à ce courriel.",
        "text_contact_header": "Nouvelle demande de contact",
        "text_contact_from": "De",
        "text_contact_subject_label": "Objet",
        "text_contact_message_label": "Message",
        "text_contact_reply_hint": "Répondez depuis le panneau d'administration.",
        "reply_subject": "Re : {{ subject }}",
        "reply_title": "Re : {{ subject }}",
        "reply_preheader": "{{ brand_name }} a répondu à votre demande",
        "reply_greeting": "Bonjour {{ name }},",
        "reply_intro": "Merci de nous avoir contactés. Veuillez trouver notre réponse ci-dessous.",
        "reply_heading": "Re : {{ subject }}",
        "reply_original_label": "Votre message original",
        "reply_signoff": "Cordialement,",
        "reply_footer": "Vous recevez ce message parce que vous avez envoyé une demande via notre site web.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un message de {{ brand_name }}",
        "new_email_greeting": "Bonjour{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Nous espérons que ce message vous trouvera en bonne santé.",
        "new_email_signoff": "Cordialement,",
        "new_email_footer": "Cet e-mail a été envoyé par {{ brand_name }}.",
    },
    "de": {
        "contact_subject": "[{{ brand_name }}] Neue Anfrage: {{ subject }}",
        "contact_title": "Neue Kontaktnachricht: {{ subject }}",
        "contact_preheader": "Neue Nachricht von {{ name }} bezüglich &bdquo;{{ subject }}&ldquo;",
        "contact_body_intro": "Sie haben eine neue Anfrage über das Kontaktformular Ihres Portfolios erhalten.",
        "contact_action_html": 'Sie können direkt aus dem <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">Admin-Panel</a> auf diese Nachricht antworten.',
        "contact_footer": "Dies ist eine automatische Benachrichtigung. Bitte antworten Sie nicht direkt auf diese E-Mail.",
        "text_contact_header": "Neue Kontaktanfrage",
        "text_contact_from": "Von",
        "text_contact_subject_label": "Betreff",
        "text_contact_message_label": "Nachricht",
        "text_contact_reply_hint": "Antworten Sie über das Admin-Panel.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} hat auf Ihre Anfrage geantwortet",
        "reply_greeting": "Hallo {{ name }},",
        "reply_intro": "Vielen Dank für Ihre Anfrage. Unsere Antwort finden Sie unten.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "Ihre ursprüngliche Nachricht",
        "reply_signoff": "Mit freundlichen Grüßen,",
        "reply_footer": "Sie erhalten diese E-Mail, weil Sie eine Anfrage über unsere Website gesendet haben.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Eine Nachricht von {{ brand_name }}",
        "new_email_greeting": "Hallo{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Wir hoffen, dass es Ihnen gut geht.",
        "new_email_signoff": "Mit freundlichen Grüßen,",
        "new_email_footer": "Diese E-Mail wurde von {{ brand_name }} gesendet.",
    },
    "zh-hans": {
        "contact_subject": "[{{ brand_name }}] 新咨询：{{ subject }}",
        "contact_title": "新的联系消息：{{ subject }}",
        "contact_preheader": "来自 {{ name }} 关于 &quot;{{ subject }}&quot; 的新消息",
        "contact_body_intro": "您通过作品集联系表单收到了一份新咨询。",
        "contact_action_html": '您可以直接通过<a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">管理后台</a>回复此消息。',
        "contact_footer": "这是一封自动通知邮件，请勿直接回复。",
        "text_contact_header": "新的联系咨询",
        "text_contact_from": "来自",
        "text_contact_subject_label": "主题",
        "text_contact_message_label": "消息内容",
        "text_contact_reply_hint": "请通过管理后台回复。",
        "reply_subject": "回复：{{ subject }}",
        "reply_title": "回复：{{ subject }}",
        "reply_preheader": "{{ brand_name }} 已回复您的咨询",
        "reply_greeting": "您好 {{ name }}，",
        "reply_intro": "感谢您的来信，以下是我们的回复。",
        "reply_heading": "回复：{{ subject }}",
        "reply_original_label": "您的原始留言",
        "reply_signoff": "此致敬礼，",
        "reply_footer": "您收到此邮件是因为您通过我们的网站发送了咨询。",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "来自 {{ brand_name }} 的信息",
        "new_email_greeting": "您好{% if name %} {{ name }}{% endif %}，",
        "new_email_intro": "希望这封邮件能够顺利送达。",
        "new_email_signoff": "此致敬礼，",
        "new_email_footer": "此邮件由 {{ brand_name }} 发送。",
    },
    "ja": {
        "contact_subject": "[{{ brand_name }}] 新しいお問い合わせ：{{ subject }}",
        "contact_title": "新しいお問い合わせ：{{ subject }}",
        "contact_preheader": "{{ name }} 様より「{{ subject }}」についての新しいメッセージ",
        "contact_body_intro": "ポートフォリオのお問い合わせフォームから新しいご連絡が届きました。",
        "contact_action_html": 'このメッセージには<a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">管理パネル</a>から直接返信できます。',
        "contact_footer": "これは自動送信メールです。このメールには返信しないでください。",
        "text_contact_header": "新しいお問い合わせ",
        "text_contact_from": "差出人",
        "text_contact_subject_label": "件名",
        "text_contact_message_label": "メッセージ",
        "text_contact_reply_hint": "管理パネルからご返信ください。",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} からのご回答",
        "reply_greeting": "{{ name }} 様",
        "reply_intro": "お問い合わせいただきありがとうございます。以下に回答をお送りいたします。",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "お客様のメッセージ",
        "reply_signoff": "敬具",
        "reply_footer": "このメールは、当ウェブサイトからお問い合わせをいただいたためお送りしています。",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} からのお知らせ",
        "new_email_greeting": "{% if name %}{{ name }} 様{% else %}関係者各位{% endif %}",
        "new_email_intro": "平素は格別のご高配を賜り、誠にありがとうございます。",
        "new_email_signoff": "敬具",
        "new_email_footer": "このメールは {{ brand_name }} から送信されました。",
    },
    "ar": {
        "contact_subject": "[{{ brand_name }}] استفسار جديد: {{ subject }}",
        "contact_title": "رسالة تواصل جديدة: {{ subject }}",
        "contact_preheader": "رسالة جديدة من {{ name }} بشأن &laquo;{{ subject }}&raquo;",
        "contact_body_intro": "لقد تلقيت استفسارًا جديدًا عبر نموذج التواصل في معرض أعمالك.",
        "contact_action_html": 'يمكنك الرد على هذه الرسالة مباشرة من <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">لوحة الإدارة</a>.',
        "contact_footer": "هذا إشعار تلقائي. يرجى عدم الرد مباشرة على هذه الرسالة.",
        "text_contact_header": "استفسار تواصل جديد",
        "text_contact_from": "من",
        "text_contact_subject_label": "الموضوع",
        "text_contact_message_label": "الرسالة",
        "text_contact_reply_hint": "الرد عبر لوحة الإدارة.",
        "reply_subject": "رد: {{ subject }}",
        "reply_title": "رد: {{ subject }}",
        "reply_preheader": "لقد رد {{ brand_name }} على استفسارك",
        "reply_greeting": "مرحبًا {{ name }}،",
        "reply_intro": "شكرًا لتواصلك معنا. تجد ردنا أدناه.",
        "reply_heading": "رد: {{ subject }}",
        "reply_original_label": "رسالتك الأصلية",
        "reply_signoff": "مع أطيب التحيات،",
        "reply_footer": "لقد تلقيت هذه الرسالة لأنك أرسلت استفسارًا عبر موقعنا.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "رسالة من {{ brand_name }}",
        "new_email_greeting": "مرحبًا{% if name %} {{ name }}{% endif %}،",
        "new_email_intro": "نأمل أن تكون هذه الرسالة قد وصلتك وأنت بخير.",
        "new_email_signoff": "مع أطيب التحيات،",
        "new_email_footer": "تم إرسال هذه الرسالة من {{ brand_name }}.",
    },
    "pt": {
        "contact_subject": "[{{ brand_name }}] Nova consulta: {{ subject }}",
        "contact_title": "Nova mensagem de contacto: {{ subject }}",
        "contact_preheader": "Nova mensagem de {{ name }} sobre &quot;{{ subject }}&quot;",
        "contact_body_intro": "Recebeu uma nova consulta através do formulário de contacto do seu portfólio.",
        "contact_action_html": 'Pode responder a esta mensagem diretamente a partir do <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">painel de administração</a>.',
        "contact_footer": "Esta é uma notificação automática. Por favor, não responda diretamente a este e-mail.",
        "text_contact_header": "Nova consulta de contacto",
        "text_contact_from": "De",
        "text_contact_subject_label": "Assunto",
        "text_contact_message_label": "Mensagem",
        "text_contact_reply_hint": "Responda através do painel de administração.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} respondeu à sua consulta",
        "reply_greeting": "Olá {{ name }},",
        "reply_intro": "Obrigado pelo seu contacto. Segue abaixo a nossa resposta.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "A sua mensagem original",
        "reply_signoff": "Com os melhores cumprimentos,",
        "reply_footer": "Está a receber este e-mail porque enviou uma consulta através do nosso site.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Uma mensagem de {{ brand_name }}",
        "new_email_greeting": "Olá{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Esperamos que esta mensagem o encontre bem.",
        "new_email_signoff": "Com os melhores cumprimentos,",
        "new_email_footer": "Este e-mail foi enviado por {{ brand_name }}.",
    },
    "ru": {
        "contact_subject": "[{{ brand_name }}] Новый запрос: {{ subject }}",
        "contact_title": "Новое сообщение через форму: {{ subject }}",
        "contact_preheader": "Новое сообщение от {{ name }} по поводу &laquo;{{ subject }}&raquo;",
        "contact_body_intro": "Через форму обратной связи вашего портфолио поступил новый запрос.",
        "contact_action_html": 'Вы можете ответить на это сообщение прямо из <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">панели администратора</a>.',
        "contact_footer": "Это автоматическое уведомление. Пожалуйста, не отвечайте на это письмо напрямую.",
        "text_contact_header": "Новый запрос через форму",
        "text_contact_from": "От",
        "text_contact_subject_label": "Тема",
        "text_contact_message_label": "Сообщение",
        "text_contact_reply_hint": "Отвечайте через панель администратора.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ответил(а) на ваш запрос",
        "reply_greeting": "Здравствуйте, {{ name }}!",
        "reply_intro": "Благодарим вас за обращение. Наш ответ приведён ниже.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "Ваше исходное сообщение",
        "reply_signoff": "С наилучшими пожеланиями,",
        "reply_footer": "Вы получили это письмо, так как отправили запрос через наш сайт.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Сообщение от {{ brand_name }}",
        "new_email_greeting": "Здравствуйте{% if name %}, {{ name }}{% endif %}!",
        "new_email_intro": "Надеемся, у вас всё хорошо.",
        "new_email_signoff": "С наилучшими пожеланиями,",
        "new_email_footer": "Это письмо отправлено от {{ brand_name }}.",
    },
    "bn": {
        "contact_subject": "[{{ brand_name }}] নতুন অনুসন্ধান: {{ subject }}",
        "contact_title": "নতুন যোগাযোগ বার্তা: {{ subject }}",
        "contact_preheader": "&quot;{{ subject }}&quot; বিষয়ে {{ name }} এর কাছ থেকে নতুন বার্তা",
        "contact_body_intro": "আপনি আপনার পোর্টফোলিও যোগাযোগ ফর্মের মাধ্যমে একটি নতুন অনুসন্ধান পেয়েছেন।",
        "contact_action_html": 'আপনি সরাসরি <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">অ্যাডমিন প্যানেল</a> থেকে এই বার্তার উত্তর দিতে পারেন।',
        "contact_footer": "এটি একটি স্বয়ংক্রিয় বিজ্ঞপ্তি। অনুগ্রহ করে এই ইমেলে সরাসরি উত্তর দেবেন না।",
        "text_contact_header": "নতুন যোগাযোগ অনুসন্ধান",
        "text_contact_from": "প্রেরক",
        "text_contact_subject_label": "বিষয়",
        "text_contact_message_label": "বার্তা",
        "text_contact_reply_hint": "অ্যাডমিন প্যানেলের মাধ্যমে উত্তর দিন।",
        "reply_subject": "প্রতিউত্তর: {{ subject }}",
        "reply_title": "প্রতিউত্তর: {{ subject }}",
        "reply_preheader": "{{ brand_name }} আপনার অনুসন্ধানের উত্তর দিয়েছেন",
        "reply_greeting": "প্রিয় {{ name }},",
        "reply_intro": "যোগাযোগ করার জন্য ধন্যবাদ। নিচে আমাদের উত্তর দেওয়া হলো।",
        "reply_heading": "প্রতিউত্তর: {{ subject }}",
        "reply_original_label": "আপনার মূল বার্তা",
        "reply_signoff": "শুভেচ্ছান্তে,",
        "reply_footer": "আপনি আমাদের ওয়েবসাইটে অনুসন্ধান পাঠানোর কারণে এই ইমেলটি পাচ্ছেন।",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} থেকে একটি বার্তা",
        "new_email_greeting": "প্রিয়{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "আশা করি এই বার্তাটি আপনাকে সুস্থ অবস্থায় খুঁজে পাবে।",
        "new_email_signoff": "শুভেচ্ছান্তে,",
        "new_email_footer": "এই ইমেলটি {{ brand_name }} দ্বারা প্রেরণ করা হয়েছে।",
    },
    "hi": {
        "contact_subject": "[{{ brand_name }}] नई पूछताछ: {{ subject }}",
        "contact_title": "नया संपर्क संदेश: {{ subject }}",
        "contact_preheader": "&quot;{{ subject }}&quot; के बारे में {{ name }} की ओर से नया संदेश",
        "contact_body_intro": "आपको अपने पोर्टफोलियो संपर्क फॉर्म के माध्यम से एक नई पूछताछ प्राप्त हुई है।",
        "contact_action_html": 'आप इस संदेश का उत्तर सीधे <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">एडमिन पैनल</a> से दे सकते हैं।',
        "contact_footer": "यह एक स्वचालित सूचना है। कृपया इस ईमेल का सीधे उत्तर न दें।",
        "text_contact_header": "नई संपर्क पूछताछ",
        "text_contact_from": "प्रेषक",
        "text_contact_subject_label": "विषय",
        "text_contact_message_label": "संदेश",
        "text_contact_reply_hint": "एडमिन पैनल के माध्यम से उत्तर दें।",
        "reply_subject": "उत्तर: {{ subject }}",
        "reply_title": "उत्तर: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ने आपकी पूछताछ का उत्तर दिया है",
        "reply_greeting": "नमस्ते {{ name }},",
        "reply_intro": "संपर्क करने के लिए धन्यवाद। हमारा उत्तर नीचे दिया गया है।",
        "reply_heading": "उत्तर: {{ subject }}",
        "reply_original_label": "आपका मूल संदेश",
        "reply_signoff": "सादर,",
        "reply_footer": "आप यह ईमेल इसलिए प्राप्त कर रहे हैं क्योंकि आपने हमारी वेबसाइट के माध्यम से एक पूछताछ भेजी थी।",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} की ओर से एक संदेश",
        "new_email_greeting": "नमस्ते{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "हम आशा करते हैं कि यह संदेश आपको कुशल पाएगा।",
        "new_email_signoff": "सादर,",
        "new_email_footer": "यह ईमेल {{ brand_name }} द्वारा भेजा गया है।",
    },
    "ur": {
        "contact_subject": "[{{ brand_name }}] نیا استفسار: {{ subject }}",
        "contact_title": "نیا رابطہ پیغام: {{ subject }}",
        "contact_preheader": "&quot;{{ subject }}&quot; کے بارے میں {{ name }} کی جانب سے نیا پیغام",
        "contact_body_intro": "آپ کو اپنے پورٹ فولیو کے رابطہ فارم کے ذریعے ایک نیا استفسار موصول ہوا ہے۔",
        "contact_action_html": 'آپ اس پیغام کا جواب براہ راست <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">ایڈمن پینل</a> سے دے سکتے ہیں۔',
        "contact_footer": "یہ ایک خودکار اطلاع ہے۔ براہ کرم اس ای میل کا براہ راست جواب نہ دیں۔",
        "text_contact_header": "نیا رابطہ استفسار",
        "text_contact_from": "بھیجنے والا",
        "text_contact_subject_label": "موضوع",
        "text_contact_message_label": "پیغام",
        "text_contact_reply_hint": "ایڈمن پینل کے ذریعے جواب دیں۔",
        "reply_subject": "جواب: {{ subject }}",
        "reply_title": "جواب: {{ subject }}",
        "reply_preheader": "{{ brand_name }} نے آپ کے استفسار کا جواب دیا ہے",
        "reply_greeting": "السلام علیکم {{ name }}،",
        "reply_intro": "رابطہ کرنے کے لیے شکریہ۔ ہمارا جواب ذیل میں موجود ہے۔",
        "reply_heading": "جواب: {{ subject }}",
        "reply_original_label": "آپ کا اصل پیغام",
        "reply_signoff": "مخلص،",
        "reply_footer": "آپ کو یہ ای میل اس لیے موصول ہوئی ہے کیونکہ آپ نے ہماری ویب سائٹ کے ذریعے استفسار بھیجا تھا۔",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} کی جانب سے ایک پیغام",
        "new_email_greeting": "السلام علیکم{% if name %} {{ name }}{% endif %}،",
        "new_email_intro": "امید ہے کہ آپ خیریت سے ہوں گے۔",
        "new_email_signoff": "مخلص،",
        "new_email_footer": "یہ ای میل {{ brand_name }} کی جانب سے بھیجی گئی ہے۔",
    },
    "ko": {
        "contact_subject": "[{{ brand_name }}] 새 문의: {{ subject }}",
        "contact_title": "새 문의 메시지: {{ subject }}",
        "contact_preheader": "&quot;{{ subject }}&quot;에 관한 {{ name }}님의 새 메시지",
        "contact_body_intro": "포트폴리오 연락 양식을 통해 새로운 문의를 받으셨습니다.",
        "contact_action_html": '이 메시지에는 <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">관리자 페이지</a>에서 직접 답장하실 수 있습니다.',
        "contact_footer": "이 메일은 자동 발송된 알림입니다. 본 메일에는 직접 답장하지 마시기 바랍니다.",
        "text_contact_header": "새 문의 접수",
        "text_contact_from": "보낸 사람",
        "text_contact_subject_label": "제목",
        "text_contact_message_label": "메시지",
        "text_contact_reply_hint": "관리자 페이지에서 답장해 주세요.",
        "reply_subject": "답장: {{ subject }}",
        "reply_title": "답장: {{ subject }}",
        "reply_preheader": "{{ brand_name }}님이 문의에 답변드렸습니다",
        "reply_greeting": "{{ name }}님, 안녕하세요.",
        "reply_intro": "문의해 주셔서 감사합니다. 아래에서 답변을 확인해 주세요.",
        "reply_heading": "답장: {{ subject }}",
        "reply_original_label": "보내주신 원문",
        "reply_signoff": "감사합니다.",
        "reply_footer": "저희 웹사이트를 통해 문의를 남겨주셔서 이 이메일을 보내드립니다.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }}의 메시지",
        "new_email_greeting": "{% if name %}{{ name }}님, {% endif %}안녕하세요.",
        "new_email_intro": "늘 평안하시기를 바랍니다.",
        "new_email_signoff": "감사합니다.",
        "new_email_footer": "이 이메일은 {{ brand_name }}에서 발송되었습니다.",
    },
    "tr": {
        "contact_subject": "[{{ brand_name }}] Yeni sorgu: {{ subject }}",
        "contact_title": "Yeni iletişim mesajı: {{ subject }}",
        "contact_preheader": "{{ name }} tarafından &quot;{{ subject }}&quot; hakkında yeni mesaj",
        "contact_body_intro": "Portföy iletişim formunuz aracılığıyla yeni bir sorgu aldınız.",
        "contact_action_html": 'Bu mesaja doğrudan <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">yönetim panelinden</a> yanıt verebilirsiniz.',
        "contact_footer": "Bu otomatik bir bildirimdir. Lütfen bu e-postayı doğrudan yanıtlamayın.",
        "text_contact_header": "Yeni iletişim sorgusu",
        "text_contact_from": "Gönderen",
        "text_contact_subject_label": "Konu",
        "text_contact_message_label": "Mesaj",
        "text_contact_reply_hint": "Yönetim panelinden yanıtlayın.",
        "reply_subject": "Yanıt: {{ subject }}",
        "reply_title": "Yanıt: {{ subject }}",
        "reply_preheader": "{{ brand_name }} sorgunuza yanıt verdi",
        "reply_greeting": "Merhaba {{ name }},",
        "reply_intro": "Bize ulaştığınız için teşekkür ederiz. Cevabımızı aşağıda bulabilirsiniz.",
        "reply_heading": "Yanıt: {{ subject }}",
        "reply_original_label": "Orijinal mesajınız",
        "reply_signoff": "Saygılarımla,",
        "reply_footer": "Bu e-postayı, web sitemiz üzerinden bir sorgu gönderdiğiniz için alıyorsunuz.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "{{ brand_name }} tarafından bir mesaj",
        "new_email_greeting": "Merhaba{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Umarız bu mesaj size iyi bir günde ulaşır.",
        "new_email_signoff": "Saygılarımla,",
        "new_email_footer": "Bu e-posta {{ brand_name }} tarafından gönderildi.",
    },
    "ro": {
        "contact_subject": "[{{ brand_name }}] Solicitare nouă: {{ subject }}",
        "contact_title": "Mesaj de contact nou: {{ subject }}",
        "contact_preheader": "Mesaj nou de la {{ name }} privind &bdquo;{{ subject }}&rdquo;",
        "contact_body_intro": "Ați primit o nouă solicitare prin formularul de contact al portofoliului dumneavoastră.",
        "contact_action_html": 'Puteți răspunde la acest mesaj direct din <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">panoul de administrare</a>.',
        "contact_footer": "Aceasta este o notificare automată. Vă rugăm să nu răspundeți direct la acest e-mail.",
        "text_contact_header": "Solicitare de contact nouă",
        "text_contact_from": "De la",
        "text_contact_subject_label": "Subiect",
        "text_contact_message_label": "Mesaj",
        "text_contact_reply_hint": "Răspundeți prin panoul de administrare.",
        "reply_subject": "Răspuns: {{ subject }}",
        "reply_title": "Răspuns: {{ subject }}",
        "reply_preheader": "{{ brand_name }} a răspuns la solicitarea dumneavoastră",
        "reply_greeting": "Bună ziua, {{ name }},",
        "reply_intro": "Vă mulțumim că ne-ați contactat. Răspunsul nostru se află mai jos.",
        "reply_heading": "Răspuns: {{ subject }}",
        "reply_original_label": "Mesajul dumneavoastră original",
        "reply_signoff": "Cu stimă,",
        "reply_footer": "Primiți acest e-mail deoarece ați trimis o solicitare prin intermediul site-ului nostru.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un mesaj de la {{ brand_name }}",
        "new_email_greeting": "Bună ziua{% if name %}, {{ name }}{% endif %},",
        "new_email_intro": "Sperăm că acest mesaj vă găsește bine.",
        "new_email_signoff": "Cu stimă,",
        "new_email_footer": "Acest e-mail a fost trimis de {{ brand_name }}.",
    },
    "hu": {
        "contact_subject": "[{{ brand_name }}] Új megkeresés: {{ subject }}",
        "contact_title": "Új kapcsolatfelvételi üzenet: {{ subject }}",
        "contact_preheader": "Új üzenet {{ name }} részéről, tárgya: &bdquo;{{ subject }}&rdquo;",
        "contact_body_intro": "Új megkeresést kapott a portfólió kapcsolatfelvételi űrlapján keresztül.",
        "contact_action_html": 'Erre az üzenetre közvetlenül a <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">adminisztrációs felületről</a> válaszolhat.',
        "contact_footer": "Ez egy automatikus értesítés. Kérjük, ne válaszoljon közvetlenül erre az e-mailre.",
        "text_contact_header": "Új kapcsolatfelvételi megkeresés",
        "text_contact_from": "Feladó",
        "text_contact_subject_label": "Tárgy",
        "text_contact_message_label": "Üzenet",
        "text_contact_reply_hint": "Válaszoljon az adminisztrációs felületen keresztül.",
        "reply_subject": "Válasz: {{ subject }}",
        "reply_title": "Válasz: {{ subject }}",
        "reply_preheader": "{{ brand_name }} válaszolt megkeresésére",
        "reply_greeting": "Tisztelt {{ name }}!",
        "reply_intro": "Köszönjük megkeresését. Válaszunkat alább találja.",
        "reply_heading": "Válasz: {{ subject }}",
        "reply_original_label": "Az Ön eredeti üzenete",
        "reply_signoff": "Üdvözlettel,",
        "reply_footer": "Azért kapja ezt az e-mailt, mert érdeklődést küldött a webhelyünkön keresztül.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Üzenet a következőtől: {{ brand_name }}",
        "new_email_greeting": "Tisztelt{% if name %} {{ name }}{% endif %}!",
        "new_email_intro": "Reméljük, jól van.",
        "new_email_signoff": "Üdvözlettel,",
        "new_email_footer": "Ezt az e-mailt a {{ brand_name }} küldte.",
    },
    "it": {
        "contact_subject": "[{{ brand_name }}] Nuova richiesta: {{ subject }}",
        "contact_title": "Nuovo messaggio di contatto: {{ subject }}",
        "contact_preheader": "Nuovo messaggio da {{ name }} riguardo &quot;{{ subject }}&quot;",
        "contact_body_intro": "Hai ricevuto una nuova richiesta tramite il modulo di contatto del tuo portfolio.",
        "contact_action_html": 'Puoi rispondere a questo messaggio direttamente dal <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">pannello di amministrazione</a>.',
        "contact_footer": "Questa è una notifica automatica. Si prega di non rispondere direttamente a questa email.",
        "text_contact_header": "Nuova richiesta di contatto",
        "text_contact_from": "Da",
        "text_contact_subject_label": "Oggetto",
        "text_contact_message_label": "Messaggio",
        "text_contact_reply_hint": "Rispondi tramite il pannello di amministrazione.",
        "reply_subject": "Re: {{ subject }}",
        "reply_title": "Re: {{ subject }}",
        "reply_preheader": "{{ brand_name }} ha risposto alla tua richiesta",
        "reply_greeting": "Ciao {{ name }},",
        "reply_intro": "Grazie per averci contattato. Di seguito trova la nostra risposta.",
        "reply_heading": "Re: {{ subject }}",
        "reply_original_label": "Il tuo messaggio originale",
        "reply_signoff": "Cordiali saluti,",
        "reply_footer": "Ricevi questa email perché hai inviato una richiesta tramite il nostro sito web.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Un messaggio da {{ brand_name }}",
        "new_email_greeting": "Ciao{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Speriamo che questo messaggio la trovi bene.",
        "new_email_signoff": "Cordiali saluti,",
        "new_email_footer": "Questa email è stata inviata da {{ brand_name }}.",
    },
    "sm": {
        "contact_subject": "[{{ brand_name }}] Fesili fou: {{ subject }}",
        "contact_title": "Savali fou: {{ subject }}",
        "contact_preheader": "Savali fou mai {{ name }} e uiga i le &quot;{{ subject }}&quot;",
        "contact_body_intro": "Ua e maua se fesili fou e ala i lau fomu faafesootai i lau lisi galuega.",
        "contact_action_html": 'E mafai ona e tali sao i lenei savali mai le <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">laupapa o le pulega</a>.',
        "contact_footer": "Ole faailoaga otometi lenei. Faamolemole aua le tali sao i lenei imeli.",
        "text_contact_header": "Fesili fou",
        "text_contact_from": "Mai",
        "text_contact_subject_label": "Autu",
        "text_contact_message_label": "Savali",
        "text_contact_reply_hint": "Tali e ala i le laupapa o le pulega.",
        "reply_subject": "Tali: {{ subject }}",
        "reply_title": "Tali: {{ subject }}",
        "reply_preheader": "Ua tali mai {{ brand_name }} i lau fesili",
        "reply_greeting": "Talofa {{ name }},",
        "reply_intro": "Faafetai mo le faafesootai mai. Ole tali lea ua tuuina atu i lalo.",
        "reply_heading": "Tali: {{ subject }}",
        "reply_original_label": "Lau savali muamua",
        "reply_signoff": "Faafetai tele,",
        "reply_footer": "O loo e maua le imeli lenei talu ai sa e tuuina mai sau fesili e ala i la matou upega tafailagi.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "Se savali mai {{ brand_name }}",
        "new_email_greeting": "Talofa{% if name %} {{ name }}{% endif %},",
        "new_email_intro": "Matou te faamoemoe e maua oe i le soifua maloloina.",
        "new_email_signoff": "Faafetai tele,",
        "new_email_footer": "O lenei imeli na auina mai e {{ brand_name }}.",
    },
    "mi": {
        "contact_subject": "[{{ brand_name }}] Pātai hou: {{ subject }}",
        "contact_title": "Karere whakapā hou: {{ subject }}",
        "contact_preheader": "Karere hou mai i {{ name }} mō te &quot;{{ subject }}&quot;",
        "contact_body_intro": "Kua whiwhi koe i tētahi pātai hou mā te puka whakapā o tō kohinga mahi.",
        "contact_action_html": 'Ka taea e koe te whakautu i tēnei karere mai i te <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">paewhiri whakahaere</a>.',
        "contact_footer": "He pānui aunoa tēnei. Tēnā, kaua e whakautu tika ki tēnei īmēra.",
        "text_contact_header": "Pātai whakapā hou",
        "text_contact_from": "Nā",
        "text_contact_subject_label": "Kaupapa",
        "text_contact_message_label": "Karere",
        "text_contact_reply_hint": "Whakautua mā te paewhiri whakahaere.",
        "reply_subject": "Whakautu: {{ subject }}",
        "reply_title": "Whakautu: {{ subject }}",
        "reply_preheader": "Kua whakautu {{ brand_name }} ki tāu pātai",
        "reply_greeting": "Tēnā koe {{ name }},",
        "reply_intro": "Tēnā koe i tō tuku mai. Tērā tā mātou whakautu kei raro nei.",
        "reply_heading": "Whakautu: {{ subject }}",
        "reply_original_label": "Tāu karere taketake",
        "reply_signoff": "Ngā mihi,",
        "reply_footer": "Kei te tae atu tēnei īmēra ki a koe nā te mea i tukuna e koe he pātai mā tō mātou paetukutuku.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "He karere mai i {{ brand_name }}",
        "new_email_greeting": "Tēnā koe{% if name %}, {{ name }}{% endif %},",
        "new_email_intro": "Ko te tūmanako kei te ora koe.",
        "new_email_signoff": "Ngā mihi,",
        "new_email_footer": "I tukuna tēnei īmēra e {{ brand_name }}.",
    },
    "fa": {
        "contact_subject": "[{{ brand_name }}] درخواست جدید: {{ subject }}",
        "contact_title": "پیام تماس جدید: {{ subject }}",
        "contact_preheader": "پیام جدید از {{ name }} درباره &laquo;{{ subject }}&raquo;",
        "contact_body_intro": "شما درخواستی جدید از طریق فرم تماس نمونه‌کارهای خود دریافت کرده‌اید.",
        "contact_action_html": 'می‌توانید مستقیماً از طریق <a href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">پنل مدیریت</a> به این پیام پاسخ دهید.',
        "contact_footer": "این یک اعلان خودکار است. لطفاً مستقیماً به این ایمیل پاسخ ندهید.",
        "text_contact_header": "درخواست تماس جدید",
        "text_contact_from": "از طرف",
        "text_contact_subject_label": "موضوع",
        "text_contact_message_label": "پیام",
        "text_contact_reply_hint": "از طریق پنل مدیریت پاسخ دهید.",
        "reply_subject": "پاسخ: {{ subject }}",
        "reply_title": "پاسخ: {{ subject }}",
        "reply_preheader": "{{ brand_name }} به درخواست شما پاسخ داده است",
        "reply_greeting": "سلام {{ name }} عزیز،",
        "reply_intro": "از تماس شما سپاسگزاریم. پاسخ ما در ادامه آمده است.",
        "reply_heading": "پاسخ: {{ subject }}",
        "reply_original_label": "پیام اصلی شما",
        "reply_signoff": "با احترام،",
        "reply_footer": "این ایمیل را به این دلیل دریافت کرده‌اید که از طریق وب‌سایت ما درخواستی ارسال کرده‌اید.",
        "new_email_subject": "{{ subject }}",
        "new_email_title": "{{ subject }}",
        "new_email_preheader": "پیامی از {{ brand_name }}",
        "new_email_greeting": "سلام{% if name %} {{ name }} عزیز{% endif %}،",
        "new_email_intro": "امیدواریم در سلامت کامل باشید.",
        "new_email_signoff": "با احترام،",
        "new_email_footer": "این ایمیل توسط {{ brand_name }} ارسال شده است.",
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

    contact_html = BASE_HTML_WRAPPER % {
        "title": s["contact_title"],
        "preheader": s["contact_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<p class="email-body-text" style="margin:0 0 8px;font-size:15px;line-height:1.7;color:#333333;">'
            + s["contact_body_intro"] +
            '</p>'

            '<h2 class="email-heading" style="margin:20px 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            '{{ subject }}'
            '</h2>'

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

            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:24px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ message }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<p class="email-meta" style="margin:0;font-size:13px;line-height:1.5;color:#888888;">'
            + s["contact_action_html"] +
            '</p>'
        ),
        "footer_text": (
            '&copy; {{ brand_name }}'
            '{% if brand_website %}'
            ' &middot; <a href="{{ brand_website }}" style="color:#999999;text-decoration:underline;">{{ brand_website }}</a>'
            '{% endif %}'
            '<br/>' + s["contact_footer"]
        ),
    }

    reply_html = BASE_HTML_WRAPPER % {
        "title": s["reply_title"],
        "preheader": s["reply_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            + s["reply_greeting"] +
            '</p>'
            '<p class="email-body-text" style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#666666;">'
            + s["reply_intro"] +
            '</p>'

            '<h2 class="email-heading" style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            + s["reply_heading"] +
            '</h2>'

            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:28px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ reply_body }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:20px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-divider" style="border-top:1px solid #e8e8e8;font-size:0;line-height:0;">&nbsp;</td>'
            '</tr>'
            '</table>'

            '<p class="email-meta" style="margin:0 0 10px;font-size:11px;font-weight:700;color:#999999;text-transform:uppercase;letter-spacing:0.8px;">'
            + s["reply_original_label"] +
            '</p>'
            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:20px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td style="padding:16px 20px;background-color:#fafafa;border-left:3px solid #d1d5db;border-radius:0 6px 6px 0;">'
            '<p style="margin:0;font-size:13px;line-height:1.6;color:#888888;white-space:pre-wrap;">{{ original_message }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            + s["reply_signoff"] +
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
            '<br/>' + s["reply_footer"]
        ),
    }

    new_email_html = BASE_HTML_WRAPPER % {
        "title": s["new_email_title"],
        "preheader": s["new_email_preheader"],
        "header_title": "{{ brand_name }}",
        "body_content": (
            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            + s["new_email_greeting"] +
            '</p>'
            '<p class="email-body-text" style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#666666;">'
            + s["new_email_intro"] +
            '</p>'

            '<h2 class="email-heading" style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e3a5f;">'
            '{{ subject }}'
            '</h2>'

            '<table role="presentation" style="width:100%%;border:none;border-spacing:0;margin-bottom:24px;" cellpadding="0" cellspacing="0">'
            '<tr>'
            '<td class="email-content-block" style="padding:22px 24px;background-color:#f8fafc;border-radius:8px;border:1px solid #e8ecf0;">'
            '<p class="email-body-text" style="margin:0;font-size:15px;line-height:1.7;color:#333333;white-space:pre-wrap;">{{ body }}</p>'
            '</td>'
            '</tr>'
            '</table>'

            '<p class="email-body-text" style="margin:0 0 4px;font-size:15px;line-height:1.7;color:#333333;">'
            + s["new_email_signoff"] +
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
            '<br/>' + s["new_email_footer"]
        ),
    }

    return {
        "contact_notification": {
            "subject": s["contact_subject"],
            "html_body": contact_html,
            "text_body": (
                f"{s['text_contact_header']}\n"
                "========================\n\n"
                f"{s['text_contact_from']}: {{{{ name }}}} <{{{{ email }}}}>\n"
                f"{s['text_contact_subject_label']}: {{{{ subject }}}}\n\n"
                f"{s['text_contact_message_label']}:\n"
                "{{ message }}\n\n"
                "---\n"
                f"{s['text_contact_reply_hint']}\n"
                "{{ brand_name }}"
            ),
        },
        "admin_reply": {
            "subject": s["reply_subject"],
            "html_body": reply_html,
            "text_body": (
                f"{s['reply_greeting']}\n\n"
                f"{s['reply_intro']}\n\n"
                f"{s['reply_heading']}\n"
                "---\n\n"
                "{{ reply_body }}\n\n"
                "---\n"
                f"{s['reply_original_label']}:\n\n"
                "{{ original_message }}\n\n"
                f"{s['reply_signoff']}\n"
                "{{ brand_name }}"
            ),
        },
        "admin_new_email": {
            "subject": s["new_email_subject"],
            "html_body": new_email_html,
            "text_body": (
                f"{s['new_email_greeting']}\n\n"
                "{{ subject }}\n"
                "---\n\n"
                "{{ body }}\n\n"
                f"{s['new_email_signoff']}\n"
                "{{ brand_name }}"
            ),
        },
    }
