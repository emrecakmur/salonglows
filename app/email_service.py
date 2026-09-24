import os
import requests

def send_password_reset_email(target_email: str, reset_code: str) -> bool:
    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()

    if not resend_api_key:
        print("[Resend Error] RESEND_API_KEY is not set in Environment Variables.")
        return False

    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "SalonGlow <onboarding@resend.dev>",
            "to": [target_email],
            "subject": f"SalonGlow - Şifre Sıfırlama Kodunuz: {reset_code}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; padding: 24px; background-color: #0f172a; color: #ffffff; border-radius: 16px; max-width: 480px; margin: 0 auto; border: 1px solid #334155;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0;">Salon<span style="color: #ec4899;">Glow</span></h1>
                    <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Şifre Sıfırlama Kodu</p>
                </div>
                
                <p style="font-size: 14px; color: #cbd5e1;">Merhaba,</p>
                <p style="font-size: 14px; color: #cbd5e1;">SalonGlow hesabınız için şifre yenileme talebinde bulundunuz. 6 haneli doğrulama kodunuz:</p>
                
                <div style="background-color: #1e293b; border: 1px solid #475569; padding: 18px; text-align: center; border-radius: 12px; margin: 24px 0;">
                    <span style="font-size: 32px; font-weight: 900; letter-spacing: 6px; color: #f472b6; font-family: monospace;">{reset_code}</span>
                </div>
                
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">Bu kod 15 dakika boyunca geçerlidir.</p>
            </div>
            """
        }

        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[Resend API] Status: {r.status_code}, Body: {r.text}")
        return r.status_code in [200, 201]

    except Exception as e:
        print(f"[Resend API Error] {e}")
        return False
