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

class FlashDealRequest(BaseModel):
    service_id: int
    is_flash_deal: bool
    discount_percent: int = 20

class LogAICampaignRequest(BaseModel):
    salon_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    campaign_type: str
    offer_details: Optional[str] = ""
    message_text: Optional[str] = ""

class AdminSubscriptionUpdateRequest(BaseModel):
    salon_id: int
    new_plan: str

class AdminDeleteSalonRequest(BaseModel):
    salon_id: int

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    salon_id = get_session_salon_id(request)
    if salon_id:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="register.html", context={"error": error})

@app.post("/register")
async def register(
    request: Request,
    salon_name: str = Form(...),
    owner_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...)
):
    salon_id = register_new_salon(salon_name, owner_name, email, password, phone, city)
    if not salon_id:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "error": "Bu e-posta adresi veya salon adı zaten kullanımda. Lütfen başka bir e-posta veya salon adı deneyin."
        })

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon_id), max_age=86400*30)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None, success: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error, "success": success})

@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    salon = authenticate_salon(email, password)
    if not salon:
        return templates.TemplateResponse(request=request, name="login.html", context={
            "error": "Geçersiz e-posta veya şifre!"
        })

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon['id']), max_age=86400*30)
    return response

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot_password.html")

@app.post("/forgot-password")
async def forgot_password(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...)
):
    email = email.strip().lower()
    reset_code = create_password_reset_code(email)
    
    if reset_code:
        background_tasks.add_task(send_password_reset_email, email, reset_code)

    return templates.TemplateResponse(request=request, name="forgot_password.html", context={
        "code_sent": True,
        "email": email,
        "success": "Eğer bu e-posta adresi sistemimizde kayıtlı ise 6 haneli şifre sıfırlama kodu gönderildi. Lütfen e-postanızı (ve spam kutunuzu) kontrol edin."
    })

@app.post("/reset-password")
async def reset_password(
    request: Request,
    email: str = Form(...),
    reset_code: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...)
):
    email = email.strip().lower()
    reset_code = reset_code.strip()

    if new_password != new_password_confirm:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "code_sent": True,
            "email": email,
            "error": "Girdiğiniz yeni şifreler birbiriyle uyuşmuyor!"
        })

    if len(new_password) < 6:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "code_sent": True,
            "email": email,
            "error": "Yeni şifreniz en az 6 karakter olmalıdır."
        })

    success = verify_and_reset_password(email, reset_code, new_password)
    if not success:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "code_sent": True,
            "email": email,
            "error": "Geçersiz veya süresi dolmuş kod! Lütfen kodu kontrol edin veya tekrar talep edin."
        })

    return templates.TemplateResponse(request=request, name="login.html", context={
        "success": "Şifreniz başarıyla sıfırlandı! Yeni şifrenizle giriş yapabilirsiniz."
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="salon_session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, date: Optional[str] = None):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return RedirectResponse(url="/login", status_code=303)

    data = get_salon_dashboard_data(salon_id, target_date=date)
    if not data:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="salon_session_id")
        return response

    return templates.TemplateResponse(request=request, name="dashboard.html", context=data)

@app.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return RedirectResponse(url="/login", status_code=303)

    data = get_salon_dashboard_data(salon_id)
    if not data:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(request=request, name="subscription.html", context=data)

@app.post("/api/appointment/new")
async def api_add_appointment(
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
        return {"status": "error", "message": "Yetkisiz erişim"}

    add_new_appointment(salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, status="APPROVED", notes=notes)
    return {"status": "success"}

@app.post("/api/appointment/delete/{appointment_id}")
async def api_delete_appointment(request: Request, appointment_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    delete_appointment(appointment_id, salon_id)
    return {"status": "success"}

@app.post("/api/package/new")
async def api_add_package(
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
        return {"status": "error", "message": "Yetkisiz erişim"}

    add_new_package(salon_id, customer_name, customer_phone, package_name, total_sessions, total_price, paid_amount)
    return {"status": "success"}

@app.post("/api/package/use/{package_id}")
async def api_use_package_session(request: Request, package_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    increment_package_session(package_id, salon_id)
    return {"status": "success"}

@app.post("/api/package/delete/{package_id}")
async def api_delete_package(request: Request, package_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    delete_customer_package(package_id, salon_id)
    return {"status": "success"}

@app.post("/api/staff/new")
async def api_add_staff(
    request: Request,
    name: str = Form(...),
    title: str = Form(...),
    color: str = Form("#ec4899")
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    add_staff_member(salon_id, name, title, color)
    return {"status": "success"}

@app.post("/api/service/new")
async def api_add_service(
    request: Request,
    name: str = Form(...),
    duration_minutes: int = Form(45),
    price: float = Form(...),
    category: str = Form(...)
):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    add_service_item(salon_id, name, duration_minutes, price, category)
    return {"status": "success"}

@app.post("/api/service/delete/{service_id}")
async def api_delete_service(request: Request, service_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    delete_service_item(service_id, salon_id)
    return {"status": "success"}

@app.post("/api/service/update-price/{service_id}")
async def api_update_service_price(request: Request, service_id: int, price: float = Form(...)):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    update_service_item(service_id, salon_id, price)
    return {"status": "success"}

@app.post("/api/service/toggle-flash-deal")
async def api_toggle_flash_deal(request: Request, req: FlashDealRequest):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    is_flash_int = 1 if req.is_flash_deal else 0
    toggle_service_flash_deal(req.service_id, salon_id, is_flash_int, req.discount_percent)
    return {"status": "success"}

@app.post("/api/salon/update-google-maps")
async def api_update_google_maps(request: Request, google_maps_url: str = Form(...)):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz erişim"}

    update_salon_google_maps(salon_id, google_maps_url)
    return {"status": "success"}

@app.get("/b/{slug}", response_class=HTMLResponse)
async def public_booking_page(request: Request, slug: str, success: Optional[str] = None):
    from app.database import get_salon_by_slug
    data = get_salon_by_slug(slug)
    if not data:
        return HTMLResponse("<h1>404 - Salon Bulunamadı</h1>", status_code=404)

    return templates.TemplateResponse(request=request, name="booking.html", context={
        "salon": data["salon"],
        "services": data["services"],
        "staff": data["staff"],
        "success": bool(success)
    })

@app.post("/b/{slug}/book")
async def public_booking_action(
    request: Request,
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

    salon_id = data["salon"]["id"]
    book_appointment_public(salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, notes=notes)
    return RedirectResponse(url=f"/b/{slug}?success=1", status_code=303)

@app.post("/api/ai/log-campaign")
async def api_log_ai_campaign(request: Request, req: LogAICampaignRequest):
    salon_id = get_session_salon_id(request) or req.salon_id
    if not salon_id:
        return {"status": "error", "message": "Yetkisiz işlem"}

    log_ai_campaign_interaction(
        salon_id=salon_id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        campaign_type=req.campaign_type,
        offer_details=req.offer_details or "",
        message_text=req.message_text or ""
    )
    return {"status": "success"}

# SUPER ADMIN ROUTES
@app.get("/admin")
async def admin_redirect_route():
    return RedirectResponse(url="/super-admin", status_code=303)

@app.get("/super-admin", response_class=HTMLResponse)
async def super_admin_page(request: Request):
    is_admin = request.cookies.get("admin_session") == "true"
    salons = get_all_salons_admin() if is_admin else []
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "is_admin": is_admin,
        "salons": salons,
        "error": None
    })

@app.post("/super-admin/login")
async def super_admin_login(request: Request, admin_password: str = Form(...)):
    valid_passwords = ["Emredadas549.", "05452772749", "admin123456", "admin2026"]
    if admin_password.strip() in valid_passwords:
        response = RedirectResponse(url="/super-admin", status_code=303)
        response.set_cookie(key="admin_session", value="true", max_age=86400*7)
        return response

    return templates.TemplateResponse(request=request, name="admin.html", context={
        "is_admin": False,
        "salons": [],
        "error": "Geçersiz admin şifresi!"
    })

@app.get("/super-admin/logout")
async def super_admin_logout():
    response = RedirectResponse(url="/super-admin", status_code=303)
    response.delete_cookie(key="admin_session")
    return response

@app.post("/api/admin/update-subscription")
async def api_admin_update_subscription(request: Request, req: AdminSubscriptionUpdateRequest):
    if request.cookies.get("admin_session") != "true":
        return {"status": "error", "message": "Yetkisiz erişim"}
    update_salon_subscription(req.salon_id, req.new_plan)
    return {"status": "success"}

@app.post("/api/admin/delete-salon")
async def api_admin_delete_salon(request: Request, req: AdminDeleteSalonRequest):
    if request.cookies.get("admin_session") != "true":
        return {"status": "error", "message": "Yetkisiz erişim"}
    delete_salon_admin(req.salon_id)
    return {"status": "success"}

@app.get("/super-admin/impersonate/{salon_id}")
async def super_admin_impersonate(request: Request, salon_id: int):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/super-admin", status_code=303)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon_id), max_age=86400*30)
    return response

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
