from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse
import uvicorn
import json
import os

app = FastAPI()
DATA_FILE = "offers.json"


# ========================== Работа с JSON ==========================
def load_offers():
    """Загружает список объявлений из файла offers.json"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_offers():
    """Сохраняет текущий список объявлений в offers.json"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=4)


# Загружаем офферы при старте
offers = load_offers()


# ========================== ГЛАВНАЯ СТРАНИЦА ==========================
@app.get("/", response_class=HTMLResponse)
def home():
    """Главная страница"""
    return """
        <h1>Добро пожаловать на сайт бартерного обмена!</h1>
        <a href="/addoffer">Добавить объявление</a><br>
        <a href="/offer">Посмотреть все объявления</a>
    """


# ========================== СТРАНИЦА ДОБАВЛЕНИЯ ОБЪЯВЛЕНИЯ ==========================
@app.get("/addoffer", response_class=HTMLResponse)
def addoffer_form():
    """Отображает HTML-форму для добавления нового объявления"""
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


# ========================== ОБРАБОТКА ФОРМЫ ДОБАВЛЕНИЯ ==========================
@app.post("/addoffer", response_class=HTMLResponse)
def addoffer_submit(give: str = Form(...), get: str = Form(...), contact: str = Form(...)):
    """Обрабатывает отправку формы и сохраняет новое объявление"""
    offers.append({"give": give, "get": get, "contact": contact})
    save_offers()

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


# ========================== СТРАНИЦА СО ВСЕМИ ОБЪЯВЛЕНИЯМИ + ПОИСК ==========================
@app.get("/offer", response_class=HTMLResponse)
def offer_list(q: str = Query(None, description="Поисковый запрос")):
    """Отображает все объявления с возможностью поиска"""

    # Если есть поисковый запрос — фильтруем список
    if q:
        filtered_offers = [
            offer for offer in offers
            if q.lower() in offer["give"].lower()
            or q.lower() in offer["get"].lower()
            or q.lower() in offer["contact"].lower()
        ]
    else:
        filtered_offers = offers

    # Генерация контента
    if not filtered_offers:
        content = "<p>Ничего не найдено 😔</p>"
    else:
        content = "<h3>Список объявлений:</h3>"
        for offer in filtered_offers:
            content += f"""
            <div style='border:1px solid #ccc; padding:10px; margin:10px; border-radius:8px;'>
                <p><b>Отдаёт:</b> {offer['give']}</p>
                <p><b>Хочет получить:</b> {offer['get']}</p>
                <p><b>Контакт для связи:</b> {offer['contact']}</p>
            </div>
            """

    # Возвращаем HTML-страницу с формой поиска
    return f"""
    <html>
        <head><title>Все объявления</title></head>
        <body>
            <h2>Все предложения пользователей</h2>

            <form method="get" action="/offer">
                <input type="text" name="q" placeholder="Поиск..." value="{q or ''}">
                <button type="submit">🔍 Найти</button>
            </form>

            <br>
            {content}
            <br>
            <a href="/addoffer">Добавить новое объявление</a><br>
            <a href="/">⬅ На главную</a>
        </body> 
    </html>
    """


# ========================== ЗАПУСК СЕРВЕРА ==========================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)