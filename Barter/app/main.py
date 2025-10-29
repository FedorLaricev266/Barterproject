from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os

app = FastAPI()

# Настройка папки с шаблонами
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- ГЛАВНАЯ СТРАНИЦА --- #
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

# --- СТРАНИЦА ДОБАВЛЕНИЯ --- #
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form(request: Request):
    return templates.TemplateResponse("addoffer.html", {"request": request})

# --- ОБРАБОТКА ФОРМЫ --- #
@app.post("/addoffer", response_class=HTMLResponse)
async def addoffer_submit(
    request: Request,
    give: str = Form(...),
    get: str = Form(...),
    contact: str = Form(...)
):
    # Передаем данные в шаблон
    context = {
        "request": request,
        "give": give,
        "get": get,
        "contact": contact
    }
    return templates.TemplateResponse("offer_added.html", context)

# --- СТРАНИЦА СО ВСЕМИ ОБЪЯВЛЕНИЯМИ --- #
@app.get("/offer", response_class=HTMLResponse)
async def offer_list(request: Request):
    return templates.TemplateResponse("offer_list.html", {"request": request})

# --- ПРОФИЛЬ --- #
@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request):
    profile_data = {
        "request": request,
        "username": "Jr.Larzyk",
        "email": "fedorlaricev6@gmail.com",
        "full_name": "Ларичев Фёдор",
        "phone": "+7 (969)735 62-37",
        "registration_date": "20.09.2025",
        "offers_count": 3,
        "successful_exchanges": 2,
        "rating": 5,
        "active_offers": [
            {"give": "Книги по программированию", "get": "Настольные игры"},
            {"give": "Гитара", "get": "Велосипед"}
        ]
    }
    return templates.TemplateResponse("profile.html", profile_data)

# --- ЗАПУСК СЕРВЕРА --- #
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)