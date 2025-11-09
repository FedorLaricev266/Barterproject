from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
import os

from db import SessionLocal, init_db, User, Offer

app = FastAPI()

# Инициализация БД
init_db()

# Настройка шаблонов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Зависимость для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Создаём гостевого пользователя
def get_guest_user(db: Session):
    user = db.query(User).filter(User.username == "Guest").first()
    if not user:
        user = User(
            username="Guest",
            email="guest@example.com",
            full_name="Гость",
            phone="-",
            rating=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# Главная
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

# Форма добавления объявления
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form(request: Request):
    return templates.TemplateResponse("addoffer.html", {"request": request})

# Добавление объявления
@app.post("/addoffer", response_class=HTMLResponse)
async def addoffer_submit(
    request: Request,
    give: str = Form(...),
    get: str = Form(...),
    contact: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_guest_user(db)
    offer = Offer(give=give, get=get, contact=contact, owner_id=user.id)
    db.add(offer)
    db.commit()
    db.refresh(offer)

    return templates.TemplateResponse("offer_added.html", {
        "request": request,
        "give": give,
        "get": get,
        "contact": contact
    })

# Список всех объявлений
@app.get("/offer", response_class=HTMLResponse)
async def offer_list(request: Request, db: Session = Depends(get_db)):
    offers = db.query(Offer).all()
    return templates.TemplateResponse("offer_list.html", {"request": request, "offers": offers})

# Профиль гостя
@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, db: Session = Depends(get_db)):
    user = get_guest_user(db)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user  # передаем весь объект User
    })

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
