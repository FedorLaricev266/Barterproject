from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from database import db
from datetime import datetime

app = FastAPI()

# Настройка папки с шаблонами
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

#ГЛАВНАЯ СТРАНИЦА
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

#СТРАНИЦА ДОБАВЛЕНИЯ
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form(request: Request):
    return templates.TemplateResponse("addoffer.html", {"request": request})

#ОБРАБОТКА ФОРМЫ 
@app.post("/addoffer", response_class=HTMLResponse)
async def addoffer_submit(
    request: Request,
    give: str = Form(...),
    get: str = Form(...),
    contact: str = Form(...)
):
    try:
        # Сохраняем объявление в базу данных
        user_id = 1 
        
        query = "INSERT INTO offers (user_id, give, `get`, contact) VALUES (%s, %s, %s, %s)"
        result = db.execute_query(query, (user_id, give, get, contact))
        
        print(f"✅ Объявление добавлено: {give} -> {get}")
        
        context = {
            "request": request,
            "give": give,
            "get": get,
            "contact": contact
        }
        return templates.TemplateResponse("offer_added.html", context)
    
    except Exception as e:
        print(f"❌ Ошибка при добавлении: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"Ошибка: {str(e)}"
        })

#СТРАНИЦА СО ВСЕМИ ОБЪЯВЛЕНИЯМИ
@app.get("/offer", response_class=HTMLResponse)
async def offer_list(request: Request):
    try:
        #все активные объявления из базы данных
        query = """
        SELECT o.*, u.username 
        FROM offers o 
        JOIN users u ON o.user_id = u.id 
        WHERE o.is_active = TRUE 
        ORDER BY o.created_at DESC
        """
        offers = db.execute_query(query, fetch=True)
        
        print(f"✅ Найдено объявлений: {len(offers) if offers else 0}")
        
        context = {
            "request": request,
            "offers": offers or []
        }
        return templates.TemplateResponse("offer_list.html", context)
    
    except Exception as e:
        print(f"❌ Ошибка загрузки объявлений: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"Ошибка загрузки объявлений: {str(e)}"
        })

#ПРОФИЛЬ
@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request):
    try:
        #пробуем найти любого пользователя
        user_query = "SELECT * FROM users ORDER BY id LIMIT 1"
        user_data = db.execute_query(user_query, fetch=True)
        
        if not user_data:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "error": "В системе нет пользователей. Сначала создайте пользователя в базе данных."
            })
        
        user = user_data[0]
        user_id = user['id']
        
        print(f"✅ Используем пользователя: {user['username']} (ID: {user_id})")
        
        #активные объявления пользователя
        offers_query = "SELECT give, `get` FROM offers WHERE user_id = %s AND is_active = TRUE"
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
            "rating": 5,
            "active_offers": active_offers
        }
        return templates.TemplateResponse("profile.html", profile_data)
    
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"Ошибка загрузки профиля: {str(e)}"
        })

#ЗАПУСК СЕРВЕРА 
if __name__ == "__main__":
    print("Запуск сервера...")
    print("Проверка подключения к БД...")
    uvicorn.run(app, host="127.0.0.1", port=8000)  