from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse
import uvicorn
import json
import os
import asyncio
from typing import List, Dict

app = FastAPI()
DATA_FILE = "offers.json"

# --- Асинхронная работа с JSON --- #
async def load_offers() -> List[Dict]:
    """Асинхронно загружает список объявлений из файла offers.json"""
    if not os.path.exists(DATA_FILE):
        return []

    # Имитация неблокирующего ввода-вывода
    await asyncio.sleep(0)  
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def save_offers():
    """Асинхронно сохраняет текущий список объявлений в offers.json"""
    await asyncio.sleep(0)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=4)


# Загружаем офферы при старте
offers: List[Dict] = asyncio.run(load_offers())

# --- ГЛАВНАЯ СТРАНИЦА --- #
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
        <h1>Добро пожаловать на сайт бартерного обмена!</h1>
        <a href="/addoffer">Добавить объявление</a><br>
        <a href="/offer">Посмотреть все объявления</a>
    """

# --- СТРАНИЦА ДОБАВЛЕНИЯ --- #
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form():
    return """
    <html>
        <head><title>Добавить объявление</title></head>
        <body>
            <h2>Добавить объявление</h2>
            <form action="/addoffer" method="post">
                <label>Что вы хотите поменять:</label><br>
                <input type="text" name="give" required><br><br>

                <label>Что вы хотите получить:</label><br>
                <input type="text" name="get" required><br><br>
                                
                <label>Контакты для связи:</label><br>
                <input type="text" name="contact" required><br><br>

                <button type="submit">Добавить</button>
            </form>
            <br>
            <a href="/">⬅ Назад на главную</a>
        </body>
    </html>
    """

# --- ОБРАБОТКА ФОРМЫ --- #
@app.post("/addoffer", response_class=HTMLResponse)
async def addoffer_submit(
    give: str = Form(...),
    get: str = Form(...),
    contact: str = Form(...)
):
    offers.append({"give": give, "get": get, "contact": contact})
    await save_offers()

    return f"""
    <html>
        <head><title>Объявление добавлено</title></head>
        <body>
            <h2>Ваше объявление добавлено!</h2>
            <p><b>Отдаёте:</b> {give}</p>
            <p><b>Получаете:</b> {get}</p>
            <p><b>Ваши контакты:</b> {contact}</p>
            <br>
            <a href="/offer">Посмотреть все объявления</a><br>
            <a href="/">⬅ На главную</a>
        </body>
    </html>
    """

# --- СТРАНИЦА СО ВСЕМИ ОБЪЯВЛЕНИЯМИ --- #
@app.get("/offer", response_class=HTMLResponse)
async def offer_list(q: str = Query(None, description="Поисковый запрос")):
    if q:
        filtered_offers = [
            offer for offer in offers
            if q.lower() in offer["give"].lower()
            or q.lower() in offer["get"].lower()
            or q.lower() in offer["contact"].lower()
        ]
    else:
        filtered_offers = offers

    if not filtered_offers:
        content = "<p>Ничего не найдено 😔</p>"
    else:
        content = "<h3>Список объявлений:</h3>"
        for offer in filtered_offers:
            content += f"""
            <div style='border:1px solid #ccc; padding:10px; margin:10px; border-radius:8px;'>
                <p><b>Отдаёт:</b> {offer['give']}</p>
                <p><b>Хочет получить:</b> {offer['get']}</p>
                <p><b>Контакт:</b> {offer['contact']}</p>
            </div>
            """

    return f"""
    <html>
        <head><title>Все объявления</title></head>
        <body>
            <h2>Все предложения пользователей</h2>

            <form method="get" action="/offer">
                <input type="text" name="q" placeholder="Поиск..." value="{q or ''}">
                <button type="submit"> Найти</button>
            </form>
<br>
            {content}
            <br>
            <a href="/addoffer">Добавить новое объявление</a><br>
            <a href="/">⬅ На главную</a>
        </body> 
    </html>
    """

# --- ПРОФИЛЬ --- #
@app.get("/profile")
async def get_profile():
    await asyncio.sleep(0)  # пример неблокирующей операции
    profile_data = {
        "username": "user123",
        "email": "user123@example.com",
        "offers_count": len(offers)
    }
    return profile_data

# --- ЗАПУСК СЕРВЕРА --- #
if name == "main":
    uvicorn.run(app, host="127.0.0.1", port=8000)
