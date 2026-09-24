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
    get_all_salons_admin,
    update_salon_subscription,
    delete_salon_admin,
    get_db
)
from app.email_service import send_password_reset_email

app = FastAPI(title="SalonGlow Multi-Tenant B2B SaaS Platform")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
def startup_event():
    init_db()

def get_session_salon_id(request: Request) -> Optional[int]:
    salon_id_str = request.cookies.get("salon_session_id")
    if salon_id_str and salon_id_str.isdigit():
        return int(salon_id_str)
    return None

class NewAppointmentRequest(BaseModel):
    salon_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    staff_name: str
    service_name: str
    appointment_date: str
    appointment_time: str
    price: float
    notes: Optional[str] = ""

class NewPackageRequest(BaseModel):
    salon_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    package_name: str
    total_sessions: int
    total_price: float
    paid_amount: float

class NewStaffRequest(BaseModel):
    name: str
    title: str

class NewServiceRequest(BaseModel):
    name: str
    duration_minutes: int
    price: float

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
async def register_submit(
    request: Request,
    name: str = Form(...),
    owner_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...)
):
    try:
        salon_id, slug = register_new_salon(name, owner_name, email, password, phone, city)
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="salon_session_id", value=str(salon_id), max_age=86400*30)
        return response
    except Exception as e:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Bu e-posta adresi veya salon adı zaten kaydolmuş."})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None, success: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error, "success": success})

@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    salon = authenticate_salon(email, password)
    if not salon:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "E-posta adresi veya şifre hatalı."})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="salon_session_id", value=str(salon['id']), max_age=86400*30)
    return response

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot_password.html")

@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, background_tasks: BackgroundTasks, email: str = Form(...)):
    code = create_password_reset_code(email)
    if not code:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "error": "Bu e-posta adresine ait kayıtlı salon bulunamadı."
        })
        
    background_tasks.add_task(send_password_reset_email, email, code)
    
    return templates.TemplateResponse(request=request, name="forgot_password.html", context={
        "email": email,
        "step": 2,
        "is_email_sent": True,
        "success": f"{email} adresinize 6 haneli doğrulama kodu e-posta olarak gönderildi! Lütfen e-posta kutunuzu (spam klasörünü dahil) kontrol edin."
    })

@app.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...)
):
    success = verify_and_reset_password(email, code.strip(), new_password)
    if not success:
        return templates.TemplateResponse(request=request, name="forgot_password.html", context={
            "email": email,
            "generated_code": code,
            "error": "Geçersiz veya süresi dolmuş kod. Lütfen tekrar deneyin."
        })
        
    return templates.TemplateResponse(request=request, name="login.html", context={
        "success": "Şifreniz başarıyla güncellendi! Yeni şifrenizle giriş yapabilirsiniz."
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="salon_session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return RedirectResponse(url="/login", status_code=303)
        
    data = get_salon_dashboard_data(salon_id=salon_id)
    if not data:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="salon_session_id")
        return response
        
    return templates.TemplateResponse(request=request, name="dashboard.html", context=data)

@app.get("/b/{slug}", response_class=HTMLResponse)
async def public_booking(request: Request, slug: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM salons WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM salons WHERE id = 1")
        row = cursor.fetchone()
    salon = dict(row)
    
    cursor.execute("SELECT * FROM staff WHERE salon_id = ?", (salon['id'],))
    staff = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM services WHERE salon_id = ?", (salon['id'],))
    services = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse(request=request, name="booking.html", context={
        "salon": salon,
        "staff": staff,
        "services": services
    })

@app.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request):
    return templates.TemplateResponse(request=request, name="subscription.html")

@app.post("/api/appointment/add")
async def api_add_appointment(request: Request, req: NewAppointmentRequest):
    salon_id = req.salon_id or get_session_salon_id(request) or 1
    new_id = add_new_appointment(
        salon_id=salon_id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        staff_name=req.staff_name,
        service_name=req.service_name,
        appointment_date=req.appointment_date,
        appointment_time=req.appointment_time,
        price=req.price,
        notes=req.notes or ""
    )
    return {"status": "success", "appointment_id": new_id}

@app.post("/api/appointment/delete/{appointment_id}")
async def api_delete_appointment(request: Request, appointment_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Oturum bulunamadı"}
    delete_appointment(appointment_id, salon_id)
    return {"status": "success"}

@app.post("/api/package/add")
async def api_add_package(request: Request, req: NewPackageRequest):
    salon_id = req.salon_id or get_session_salon_id(request) or 1
    add_new_package(
        salon_id=salon_id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        package_name=req.package_name,
        total_sessions=req.total_sessions,
        total_price=req.total_price,
        paid_amount=req.paid_amount
    )
    return {"status": "success"}

@app.post("/api/package/use/{package_id}")
async def api_use_session(package_id: int):
    increment_package_session(package_id)
    return {"status": "success"}

@app.post("/api/package/delete/{package_id}")
async def api_delete_package(request: Request, package_id: int):
    salon_id = get_session_salon_id(request)
    if not salon_id:
        return {"status": "error", "message": "Oturum bulunamadı"}
    delete_customer_package(package_id, salon_id)
    return {"status": "success"}

@app.post("/api/staff/add")
async def api_add_staff(request: Request, req: NewStaffRequest):
    salon_id = get_session_salon_id(request) or 1
    add_staff_member(salon_id, req.name, req.title)
    return {"status": "success"}

@app.post("/api/service/add")
async def api_add_service(request: Request, req: NewServiceRequest):
    salon_id = get_session_salon_id(request) or 1
    add_service_item(salon_id, req.name, req.duration_minutes, req.price)
    return {"status": "success"}

# SUPER ADMIN ROUTES
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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
