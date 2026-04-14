import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings

logger = logging.getLogger(__name__)

_CURRENT_YEAR = datetime.utcnow().year

_HTML_WRAPPER = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <!-- Outer wrapper -->
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f4f4f7;padding:40px 16px;">
    <tr>
      <td align="center">
        <!-- Email card -->
        <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

          <!-- ── HEADER ── -->
          <tr>
            <td style="background:linear-gradient(135deg,#7c3aed 0%,#4f46e5 100%);padding:32px 40px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td>
                    <table role="presentation" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background:rgba(255,255,255,.15);border-radius:8px;padding:6px 12px;font-size:18px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">
                          MF
                        </td>
                        <td style="padding-left:12px;font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
                          MediaFlow
                        </td>
                      </tr>
                    </table>
                    <p style="margin:8px 0 0;font-size:13px;color:rgba(255,255,255,.75);">
                      High-performance media conversion platform
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── CONTENT ── -->
          <tr>
            <td style="padding:40px 40px 32px;">
              {content}
            </td>
          </tr>

          <!-- ── DIVIDER ── -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:0;" />
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="padding:24px 40px 32px;text-align:center;">
              <p style="margin:0 0 4px;font-size:12px;color:#9ca3af;">
                You received this email because you requested a conversion notification on MediaFlow.
              </p>
              <p style="margin:0;font-size:12px;color:#9ca3af;">
                &copy; {year} MediaFlow. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

_CONTENT_WITH_DOWNLOAD = """\
<h1 style="margin:0 0 8px;font-size:24px;font-weight:700;color:#111827;">
  Your file is ready! &#127881;
</h1>
<p style="margin:0 0 28px;font-size:15px;color:#6b7280;">
  Your <strong style="color:#374151;">{job_type}</strong> conversion has completed successfully.
</p>

<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:28px;">
  <tr>
    <td style="padding:16px 20px;">
      <p style="margin:0 0 8px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#9ca3af;">Job details</p>
      <table role="presentation" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:13px;color:#6b7280;padding-right:12px;padding-bottom:4px;white-space:nowrap;">Type</td>
          <td style="font-size:13px;color:#111827;font-weight:500;">{job_type}</td>
        </tr>
        <tr>
          <td style="font-size:13px;color:#6b7280;padding-right:12px;white-space:nowrap;">Job ID</td>
          <td><code style="font-size:12px;color:#4f46e5;background:#ede9fe;padding:2px 6px;border-radius:4px;">{job_id}</code></td>
        </tr>
      </table>
    </td>
  </tr>
</table>

<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
  <tr>
    <td style="border-radius:8px;background:#7c3aed;">
      <a href="{download_url}"
         style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:.1px;">
        &#8615;&nbsp; Download your file
      </a>
    </td>
  </tr>
</table>

<p style="margin:0;font-size:13px;color:#9ca3af;">
  &#128274;&nbsp; This link will expire in <strong>24 hours</strong>. Download your file before it expires.
</p>
"""

_CONTENT_WITHOUT_DOWNLOAD = """\
<h1 style="margin:0 0 8px;font-size:24px;font-weight:700;color:#111827;">
  Your file is ready! &#127881;
</h1>
<p style="margin:0 0 28px;font-size:15px;color:#6b7280;">
  Your <strong style="color:#374151;">{job_type}</strong> conversion has completed successfully.
</p>

<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:28px;">
  <tr>
    <td style="padding:16px 20px;">
      <p style="margin:0 0 8px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#9ca3af;">Job details</p>
      <table role="presentation" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:13px;color:#6b7280;padding-right:12px;padding-bottom:4px;white-space:nowrap;">Type</td>
          <td style="font-size:13px;color:#111827;font-weight:500;">{job_type}</td>
        </tr>
        <tr>
          <td style="font-size:13px;color:#6b7280;padding-right:12px;white-space:nowrap;">Job ID</td>
          <td><code style="font-size:12px;color:#4f46e5;background:#ede9fe;padding:2px 6px;border-radius:4px;">{job_id}</code></td>
        </tr>
      </table>
    </td>
  </tr>
</table>

<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
  <tr>
    <td style="border-radius:8px;background:#7c3aed;">
      <a href="{app_url}"
         style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:.1px;">
        Open MediaFlow
      </a>
    </td>
  </tr>
</table>

<p style="margin:0;font-size:13px;color:#9ca3af;">
  Log in to MediaFlow to view and download your result before it expires.
</p>
"""


def _render_email(subject: str, content: str) -> str:
    return _HTML_WRAPPER.format(
        subject=subject,
        content=content,
        year=datetime.utcnow().year,
    )


def send_job_completion_email(
    to_email: str,
    job_id: str,
    job_type: str,
    download_url: str | None = None,
) -> None:
    """Send a completion notification email.

    Silently skips when SMTP_HOST is not configured so the feature remains
    optional without any code changes.
    """
    if not settings.smtp_host:
        return

    sender = settings.smtp_from or settings.smtp_user
    friendly_type = job_type.replace("_", " ").title()
    subject = f"MediaFlow – Your {friendly_type} is ready"
    app_url = settings.app_url if hasattr(settings, "app_url") else "https://mediaflow.app"

    if download_url:
        body_text = (
            f"Your {friendly_type} conversion has completed.\n\n"
            f"Job type : {friendly_type}\n"
            f"Job ID   : {job_id}\n"
            f"Download : {download_url}\n\n"
            "This link will expire in 24 hours."
        )
        content_html = _CONTENT_WITH_DOWNLOAD.format(
            job_type=friendly_type,
            job_id=job_id,
            download_url=download_url,
        )
    else:
        body_text = (
            f"Your {friendly_type} conversion has completed.\n"
            f"Job type : {friendly_type}\n"
            f"Job ID   : {job_id}\n\n"
            "Log in to MediaFlow to download your result."
        )
        content_html = _CONTENT_WITHOUT_DOWNLOAD.format(
            job_type=friendly_type,
            job_id=job_id,
            app_url=app_url,
        )

    body_html = _render_email(subject, content_html)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        if settings.smtp_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        logger.info("Completion email sent to %s for job %s", to_email, job_id)
    except Exception:
        logger.exception("Failed to send completion email to %s for job %s", to_email, job_id)
