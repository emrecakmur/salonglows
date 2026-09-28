import os
import uvicorn
from fastapi import FastAPI, Request, Form, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.database import (
    init_db,
    register_new_salon,
    authenticate_salon,
    create_password_reset_code,
    verify_and_reset_password,
    get_salon_dashboard_data,
    add_new_appointment,
    delete_appointment,
    add_new_package,
    increment_package_session,
    delete_customer_package,
    add_staff_member,
    add_service_item,
    delete_service_item,
    update_service_item,
    get_all_salons_admin,
    update_salon_subscription,
    delete_salon_admin,
    update_salon_google_maps,
    toggle_service_flash_deal,
    log_ai_campaign_interaction,
    get_db
)
from app.email_service import send_password_reset_email

app = FastAPI(title="SalonGlow Multi-Tenant B2B SaaS Platform")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
def startup_event():
    try:
        init_db()
    except Exception as e:
        print(f"Startup DB init error: {e}")

def get_session_salon_id(request: Request) -> Optional[int]:
    salon_id_str = request.cookies.get("salon_session_id")
    if salon_id_str:
        try:
            return int(salon_id_str)
        except ValueError:
            return None
    return None

@app.get("/")
def home_redirect(request: Request):
    salon_id = get_session_salon_id(request)
    if salon_id:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="register.html", context={"error": error})

@app.post("/register")
def register_action(
    name: str = Form(...),
    owner_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...)
):
    salon_id = register_new_salon(name, owner_name, email, password, phone, city)
    if not salon_id:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Bu e-posta adresi veya salon adı zaten kaydolmuş."})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon_id), httponly=True, max_age=86400*30)
    return response

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None, success: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error, "success": success})

@app.post("/login")
def login_action(email: str = Form(...), password: str = Form(...)):
    salon = authenticate_salon(email, password)
    if not salon:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "E-posta adresi veya şifre hatalı."})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon['id']), httponly=True, max_age=86400*30)
    return response

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot_password.html")

@app.post("/forgot-password")
def forgot_password_send_code(request: Request, background_tasks: BackgroundTasks, email: str = Form(...)):
    email_clean = email.lower().strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM salons WHERE email = ?", (email_clean,))
    salon = cursor.fetchone()
    conn.close()

    if not salon:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "error": "Bu e-posta adresine ait bir salon hesabı bulunamadı."
        })

    code = create_password_reset_code(email_clean)
    background_tasks.add_task(send_password_reset_email, email_clean, code)

    return templates.TemplateResponse(request=request, name="forgot_password.html", context={
        "email_sent": True,
        "email": email_clean,
        "success": "6 haneli doğrulama kodu e-posta adresinize gönderildi! (Spam klasörünü kontrol etmeyi unutmayın)"
    })

@app.post("/reset-password")
def reset_password_action(
    request: Request,
    email: str = Form(...),
    reset_code: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    email_clean = email.lower().strip()
    if new_password != confirm_password:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "email_sent": True,
            "email": email_clean,
            "error": "Girdiğiniz yeni şifreler birbiriyle uyuşmuyor!"
        })

    if len(new_password) < 6:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "email_sent": True,
            "email": email_clean,
            "error": "Yeni şifreniz en az 6 karakter olmalıdır."
        })

    success = verify_and_reset_password(email_clean, reset_code, new_password)
    if not success:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "email_sent": True,
            "email": email_clean,
            "error": "Geçersiz veya süresi dolmuş kod! Lütfen kodu kontrol edin veya tekrar talep edin."
        })

    return templates.TemplateResponse(request=request, name="login.html", context={
        "success": "Şifreniz başarıyla sıfırlandı! Yeni şifrenizle giriş yapabilirsiniz."
    })

@app.get("/logout")
def logout_action():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="salon_session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, date: Optional[str] = None):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return RedirectResponse(url="/login", status_code=303)
    
    data = get_salon_dashboard_data(salon_id, target_date=date)
    if not data:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="salon_session_id")
        return response
    
    return templates.TemplateResponse(request=request, name="dashboard.html", context=data)

class LogAICampaignRequest(BaseModel):
    customer_name: str
    customer_phone: str
    campaign_type: str
    offer_details: Optional[str] = ""
    message_text: Optional[str] = ""

@app.post("/api/ai/log-campaign")
def api_log_ai_campaign(req_data: LogAICampaignRequest, request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Giriş yapmalısınız."}
    
    log_ai_campaign_interaction(
        salon_id=salon_id,
        customer_name=req_data.customer_name,
        customer_phone=req_data.customer_phone,
        campaign_type=req_data.campaign_type,
        offer_details=req_data.offer_details,
        message_text=req_data.message_text
    )
    return {"status": "success"}

@app.get("/b/{slug}", response_class=HTMLResponse)
def public_booking_page(slug: str, request: Request, success: Optional[bool] = False):
    from app.database import get_salon_by_slug
    data = get_salon_by_slug(slug)
    if not data:
        return HTMLResponse("<h1>404 - Salon Bulunamadı</h1>", status_code=404)
    return templates.TemplateResponse(request=request, name="booking.html", context={
        "salon": data["salon"],
        "services": data["services"],
        "staff": data["staff"],
        "success": success
    })

@app.post("/b/{slug}/book")
def public_booking_action(
    slug: str,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    staff_name: str = Form(...),
    service_name: str = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    notes: Optional[str] = Form("")
):
    from app.database import get_salon_by_slug, book_appointment_public
    data = get_salon_by_slug(slug)
    if not data:
        return HTMLResponse("<h1>404 - Salon Bulunamadı</h1>", status_code=404)
    
    book_appointment_public(
        salon_id=data["salon"]["id"],
        customer_name=customer_name,
        customer_phone=customer_phone,
        staff_name=staff_name,
        service_name=service_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        notes=notes
    )
    return RedirectResponse(url=f"/b/{slug}?success=1", status_code=303)

@app.post("/api/appointment/new")
def create_appointment_api(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    staff_name: str = Form(...),
    service_name: str = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    price: float = Form(...),
    notes: Optional[str] = Form("")
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    add_new_appointment(salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, notes=notes)
    return {"status": "success"}

@app.post("/api/appointment/delete/{appointment_id}")
def delete_appointment_api(appointment_id: int, request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    delete_appointment(appointment_id, salon_id)
    return {"status": "success"}

@app.post("/api/package/new")
def create_package_api(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    package_name: str = Form(...),
    total_sessions: int = Form(...),
    total_price: float = Form(...),
    paid_amount: float = Form(...)
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    add_new_package(salon_id, customer_name, customer_phone, package_name, total_sessions, total_price, paid_amount)
    return {"status": "success"}

@app.post("/api/package/use/{package_id}")
def use_package_session_api(package_id: int, request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    increment_package_session(package_id, salon_id)
    return {"status": "success"}

@app.post("/api/package/delete/{package_id}")
def delete_package_api(package_id: int, request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    delete_customer_package(package_id, salon_id)
    return {"status": "success"}

@app.post("/api/service/new")
def add_service_api(
    request: Request,
    name: str = Form(...),
    duration_minutes: int = Form(...),
    price: float = Form(...),
    category: str = Form(...)
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    add_service_item(salon_id, name, duration_minutes, price, category)
    return {"status": "success"}

@app.post("/api/service/delete/{service_id}")
def delete_service_api(service_id: int, request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    delete_service_item(service_id, salon_id)
    return {"status": "success"}

@app.post("/api/service/update-price/{service_id}")
def update_service_price_api(service_id: int, request: Request, price: float = Form(...)):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    update_service_item(service_id, salon_id, price)
    return {"status": "success"}

@app.post("/api/staff/new")
def add_staff_api(
    request: Request,
    name: str = Form(...),
    title: str = Form(...),
    color: str = Form("#ec4899")
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    add_staff_member(salon_id, name, title, color)
    return {"status": "success"}

@app.post("/api/salon/update-google-maps")
def update_google_maps_api(request: Request, google_maps_url: str = Form(...)):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    update_salon_google_maps(salon_id, google_maps_url)
    return {"status": "success"}

@app.post("/api/service/toggle-flash/{service_id}")
def toggle_flash_deal_api(service_id: int, request: Request, is_flash: int = Form(...), discount: int = Form(20)):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}
    toggle_service_flash_deal(service_id, salon_id, is_flash, discount)
    return {"status": "success"}

@app.get("/subscription", response_class=HTMLResponse)
def subscription_page(request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="subscription.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    salons = get_all_salons_admin()
    return templates.TemplateResponse(request=request, name="admin.html", context={"salons": salons})

@app.post("/admin/update-plan/{salon_id}")
def admin_update_plan(salon_id: int, plan: str = Form(...)):
    update_salon_subscription(salon_id, plan)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/delete/{salon_id}")
def admin_delete_salon(salon_id: int):
    delete_salon_admin(salon_id)
    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
