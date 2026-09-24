import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset_email(target_email: str, reset_code: str) -> bool:
    """
    Sends a real 6-digit password reset code via SMTP if credentials exist.
    """
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

        text_content = f"""Merhaba,

SalonGlow hesabınız için şifre sıfırlama talebinde bulundunuz.

6 Haneli Doğrulama Kodunuz: {reset_code}

Bu kod 15 dakika geçerlidir.

Saygılarımızla,
SalonGlow Ekibi
"""

        html_content = f"""
        <div style="font-family: Arial, sans-serif; background-color: #0f172a; padding: 24px; color: #f8fafc; border-radius: 16px; max-width: 480px; margin: 0 auto; border: 1px solid #334155;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0;">Salon<span style="color: #ec4899;">Glow</span></h1>
                <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Şifre Sıfırlama Kodu</p>
            </div>
            
            <p style="font-size: 14px; color: #cbd5e1;">Merhaba,</p>
            <p style="font-size: 14px; color: #cbd5e1;">SalonGlow hesabınız için şifre yenileme talebinde bulundunuz. Şifrenizi güncellemek için aşağıdaki 6 haneli kodu kullanabilirsiniz:</p>
            
            <div style="background-color: #1e293b; border: 1px solid #475569; padding: 18px; text-align: center; border-radius: 12px; margin: 24px 0;">
                <span style="font-size: 32px; font-weight: 900; letter-spacing: 6px; color: #f472b6; font-family: monospace;">{reset_code}</span>
            </div>
            
            <p style="font-size: 12px; color: #94a3b8; text-align: center;">Bu kod 15 dakika boyunca geçerlidir. Talebi siz yapmadıysanız bu e-postayı dikkate almayınız.</p>
        </div>
        """

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, target_email, msg.as_string())

        return True
    except Exception as e:
        print(f"[SMTP Error] E-posta gönderilemedi: {e}")
        return False
