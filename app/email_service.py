import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset_email(target_email: str, reset_code: str) -> bool:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()

    if not smtp_user or not smtp_password:
        print("[SMTP Error] SMTP_USER or SMTP_PASSWORD not set.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"SalonGlow - Şifre Sıfırlama Kodunuz: {reset_code}"
        msg["From"] = smtp_user
        msg["To"] = target_email

        text_content = f"Merhaba,\n\nSalonGlow hesabınız için 6 haneli doğrulama kodunuz: {reset_code}\n"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #ffffff; border-radius: 12px;">
            <h2 style="color: #ec4899;">SalonGlow</h2>
            <p>Merhaba,</p>
            <p>SalonGlow hesabınız için 6 haneli doğrulama kodunuz:</p>
            <h1 style="color: #ec4899; letter-spacing: 5px;">{reset_code}</h1>
            <p style="font-size: 12px; color: #94a3b8;">Bu kod 15 dakika geçerlidir.</p>
        </div>
        """

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Try SSL Port 465 (Works 100% on Cloud platforms like Render)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, target_email, msg.as_string())
            print(f"[SMTP SUCCESS - SSL 465] Email successfully sent to {target_email}")
            return True
        except Exception as e_ssl:
            print(f"[SMTP SSL 465 Fallback] {e_ssl}, trying TLS 587...")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, target_email, msg.as_string())
            print(f"[SMTP SUCCESS - TLS 587] Email successfully sent to {target_email}")
            return True

    except Exception as e:
        print(f"[SMTP Error] Failed to send email to {target_email}: {e}")
        return False
