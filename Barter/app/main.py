from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
import uvicorn
import os
from database import db
from datetime import datetime
import shutil


app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads", "offers")
os.makedirs(UPLOAD_DIR, exist_ok=True)

print(f"Templates directory: {TEMPLATES_DIR}")
print(f"Static directory: {STATIC_DIR}")
print(f"Upload directory: {UPLOAD_DIR}")


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=404,
            content={"detail": "Страница не найдена"}
        )
    
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "error": "Страница не найдена"},
        status_code=404
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"}
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error": "Внутренняя ошибка сервера. Пожалуйста, попробуйте позже."
        },
        status_code=500
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form(request: Request):
    return templates.TemplateResponse("addoffer.html", {"request": request})


@app.post("/addoffer", response_class=HTMLResponse)
async def addoffer_submit(
    request: Request,
    give: str = Form(...),
    get: str = Form(...),
    contact: str = Form(...),
    category: str = Form(None),
    city: str = Form(None),
    district: str = Form(None),
    image: UploadFile = File(None)
):
    try:
        user_id = 1
        image_path = None
        
        if image and image.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = os.path.splitext(image.filename)[1]
            filename = f"offer_{timestamp}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            print(f"Сохраняем файл: {file_path}")
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            image_path = f"/static/uploads/offers/{filename}"
            print(f"Фото сохранено: {image_path}")
            print(f"Полный путь: {file_path}")
        
        query = """
            INSERT INTO offers (user_id, give, `get`, contact, category, city, district, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        result = db.execute_query(
            query,
            (user_id, give, get, contact, category, city, district, image_path)
        )
        
        print(f"Сохранено в БД: image_url = {image_path}")
        
        context = {
            "request": request,
            "give": give,
            "get": get,
            "contact": contact,
            "category": category,
            "city": city,
            "district": district,
            "image_path": image_path
        }
        return templates.TemplateResponse("offer_added.html", context)
    
    except Exception as e:
        print(f"Ошибка при добавлении: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка: {str(e)}"
        })


@app.get("/offer", response_class=HTMLResponse)
async def offer_list(request: Request):
    try:
        category = request.query_params.get('category', '')
        city = request.query_params.get('city', '')
        search = request.query_params.get('search', '')
        
        query = """
            SELECT o.*, u.username
            FROM offers o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.is_active = TRUE
        """
        params = []
        
        if category:
            query += " AND o.category = %s"
            params.append(category)
        
        if city:
            query += " AND o.city = %s"
            params.append(city)
            
        if search:
            query += " AND (o.give LIKE %s OR o.`get` LIKE %s OR u.username LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY o.created_at DESC"
        
        print(f"Выполняем запрос: {query}")
        print(f"Параметры: {params}")
        
        offers = db.execute_query(query, params, fetch=True)
        
        if offers is None:
            offers = []
            
        print(f"Найдено объявлений: {len(offers)}")
        for offer in offers:
            print(f"ID: {offer.get('id')}, Фото: {offer.get('image_url')}")
        
        context = {
            "request": request,
            "offers": offers,
            "current_category": category,
            "current_city": city,
            "current_search": search,
            "offers_count": len(offers)
        }
        return templates.TemplateResponse("offer_list.html", context)
    
    except Exception as e:
        print(f"Ошибка загрузки объявлений: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка загрузки объявлений: {str(e)}"
        })


@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request):
    try:
        user_query = "SELECT * FROM users ORDER BY id LIMIT 1"
        user_data = db.execute_query(user_query, fetch=True)
        
        if not user_data:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "В системе нет пользователей. Сначала создайте пользователя в базе данных."
            })
        
        user = user_data[0]
        user_id = user['id']
        
        print(f"Используем пользователя: {user['username']} (ID: {user_id})")
        
        offers_query = """
            SELECT id, give, `get`, image_url
            FROM offers
            WHERE user_id = %s AND is_active = TRUE
        """
        active_offers = db.execute_query(offers_query, (user_id,), fetch=True) or []
        
        offers_count_query = "SELECT COUNT(*) as count FROM offers WHERE user_id = %s"
        offers_count_result = db.execute_query(offers_count_query, (user_id,), fetch=True)
        offers_count = offers_count_result[0]['count'] if offers_count_result else 0
        
        profile_data = {
            "request": request,
            "username": user['username'],
            "email": user['email'],
            "full_name": user['full_name'],
            "phone": user['phone'],
            "registration_date": user['registration_date'].strftime("%d.%m.%Y"),
            "offers_count": offers_count,
            "successful_exchanges": 0,
            "rating": "ещё нет оценок (бета)",
            "active_offers": active_offers
        }
        return templates.TemplateResponse("profile.html", profile_data)
    
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка загрузки профиля: {str(e)}"
        })


@app.get("/offer/{id}", response_class=HTMLResponse)
async def offercard(request: Request, id: int):
    try:
        query = """
            SELECT o.*, u.username, u.email, u.phone
            FROM offers o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s
        """
        offer_data = db.execute_query(query, (id,), fetch=True)
        
        if not offer_data:
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        offer = offer_data[0]
        
        context = {
            "request": request,
            "offer": offer
        }
        return templates.TemplateResponse("offercard.html", context)
    
    except HTTPException:
        raise
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка загрузки объявления: {str(e)}"
        })


@app.post("/delete_offer/{offer_id}")
async def delete_offer(offer_id: int, request: Request):
    try:
        print(f"Попытка удаления объявления {offer_id}")
        
        query = "UPDATE offers SET is_active = FALSE WHERE id = %s"
        result = db.execute_query(query, (offer_id,))
        
        if result is not None:
            print(f"Объявление {offer_id} удалено")
            return {"success": True, "message": "Объявление удалено"}
        else:
            print(f"Ошибка при удалении {offer_id}")
            return {"success": False, "message": "Ошибка при удалении"}
            
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
        return {"success": False, "message": f"Ошибка сервера: {str(e)}"}


@app.get("/minigame", response_class=HTMLResponse)
async def minigame(request: Request):
    return templates.TemplateResponse("minigame.html", {"request": request})


@app.get("/test-404", response_class=HTMLResponse)
async def test_404(request: Request):
    raise HTTPException(status_code=404, detail="Тестовая 404 ошибка")


if __name__ == "__main__":
    print("Запуск сервера...")
    print("Проверка подключения к БД...")
    uvicorn.run(app, host="127.0.0.1", port=8000)