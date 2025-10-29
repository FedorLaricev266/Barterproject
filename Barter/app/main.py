from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse
import uvicorn


app = FastAPI()


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
    # Данные не сохраняются — просто отображаем пользователю
    return f"""
    <html>
        <head><title>Объявление добавлено</title></head>
        <body>
            <h2>Ваше объявление принято!</h2>
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
    # Так как мы ничего не храним — всегда показываем сообщение:
    return """
    <html>
        <head><title>Все объявления</title></head>
        <body>
            <h2>Список объявлений</h2>
            <p>Пока что объявлений нет 😔</p>
            <a href="/addoffer">Добавить новое объявление</a><br>
            <a href="/">⬅ На главную</a>
        </body>
    </html>
    """

# --- ПРОФИЛЬ (пример статического ответа) --- #
@app.get("/profile")
async def get_profile():
    
    profile_data = {
        "username": "user123",
        "email": "user123@example.com",
        "offers_count": 0
    }
    return profile_data

# --- ЗАПУСК СЕРВЕРА --- #
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)