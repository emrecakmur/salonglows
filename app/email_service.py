import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset_email(target_email: str, reset_code: str) -> bool:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"SalonGlow - Şifre Sıfırlama Kodunuz: {reset_code}"
        msg["From"] = f"SalonGlow Destek <{smtp_user}>"
        msg["To"] = target_email

        text_content = f"Merhaba,\n\nSalonGlow hesabınız için 6 haneli doğrulama kodunuz: {reset_code}\n"
        html_content = f"<h2>SalonGlow</h2><p>Doğrulama Kodunuz: <b>{reset_code}</b></p>"

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=5) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, target_email, msg.as_string())

        return True
    except Exception as e:
        print(f"[SMTP Error] {e}")
        return False
