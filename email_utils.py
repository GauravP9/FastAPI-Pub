from email.message import EmailMessage  # Construct Email
import aiosmtplib  # Sending Email
from fastapi.templating import Jinja2Templates  # HTML Email

from config import settings  # Cred of email
import resend

templates = Jinja2Templates(directory="templates")  # Keeping the email template in subdirectory


async def send_email(to_email: str, subject: str, plain_text: str, html_content: str | None = None) -> None:

    resend.api_key = settings.mail_password.get_secret_value()

    params = {
        "from": settings.mail_from,
        "to": [to_email],
        "subject": subject,
        "text": plain_text,
    }

    if html_content:
        params["html"] = html_content

    resend.Emails.send(params)


 
    message = EmailMessage()  # Email Message class to construct the message here
    message["From"] = settings.mail_from  # Info
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(plain_text)  # Plain text as fallback cause some client dont support HTML all the time

    if html_content:
        message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        message, hostname=settings.mail_server, port=settings.mail_port, username=settings.mail_username, password=settings.mail_password.get_secret_value(), start_tls=settings.mail_use_tls
    )  # Send the mail


async def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    "Password Reset"
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"  # Token are not JWT We use db based token single use once reset we delete token from the db to get single use behaviour we cant use JWT cause then we have to maintain seperate blacklist of token that are used.

    template = templates.env.get_template(
        "email/password_reset.html"
    )  # using env here instead of responce cause for responce we need req body which we dont have in reset pass, we can call env on render method which gives us rendered email address
    html_content = template.render(reset_url=reset_url, username=username)  # Calling reder to render the email here

    plain_text = f"""Hi {username},

You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, you can safely ignore this email.

Best regards,
The FastAPI Blog Team
"""

    await send_email(
        to_email=to_email,
        subject="Reset Your Password - FastAPI Blog",
        plain_text=plain_text,
        html_content=html_content,
    )  # Calling send_email fun
