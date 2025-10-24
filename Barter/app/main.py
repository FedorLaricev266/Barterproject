from fastapi import FastAPI, Form, Query, Request
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
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Главная - Бартерный обмен</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                line-height: 1.6; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px; display: flex; align-items: center; justify-content: center;
            }
            .container {
                max-width: 800px; background: white; padding: 40px; border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center;
            }
            h1 { color: #2c3e50; margin-bottom: 20px; font-size: 2.5em; }
            .hero p { font-size: 1.2em; color: #7f8c8d; margin-bottom: 40px; }
            .action-buttons { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
            .btn { 
                padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;
                transition: all 0.3s ease; display: inline-block; min-width: 200px;
            }
            .btn-primary { background: #e74c3c; color: white; }
            .btn-secondary { background: #3498db; color: white; }
            .btn-tertiary { background: #9b59b6; color: white; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="hero">
                <h1>🔄 Добро пожаловать на сайт бартерного обмена!</h1>
                <p>Находите выгодные обмены без денег • Обменивайтесь товарами и услугами</p>
                
                <div class="action-buttons">
                    <a href="/addoffer" class="btn btn-primary">➕ Добавить объявление</a>
                    <a href="/offer" class="btn btn-secondary">📋 Все объявления</a>
                    <a href="/profile" class="btn btn-tertiary">👤 Мой профиль</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# --- СТРАНИЦА ДОБАВЛЕНИЯ --- #
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Добавить объявление</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px;
            }
            .container {
                max-width: 600px; margin: 0 auto; background: white; padding: 30px;
                border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 { color: #2c3e50; margin-bottom: 30px; text-align: center; }
            label { display: block; margin-bottom: 8px; font-weight: bold; color: #2c3e50; }
            input[type="text"] {
                width: 100%; padding: 12px; margin-bottom: 20px; border: 2px solid #bdc3c7;
                border-radius: 8px; font-size: 16px; transition: border-color 0.3s;
            }
            input[type="text"]:focus {
                border-color: #3498db; outline: none; box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
            }
            button { 
                background: #27ae60; color: white; padding: 15px 30px; border: none;
                border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;
                width: 100%; transition: background 0.3s;
            }
            button:hover { background: #219a52; }
            .back-link { 
                display: inline-block; margin-top: 20px; color: #3498db; 
                text-decoration: none; text-align: center; width: 100%;
            }
            .back-link:hover { text-decoration: underline; }
            .form-group { margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📝 Добавить объявление</h2>
            
            <form action="/addoffer" method="post">
                <div class="form-group">
                    <label>🎁 Что вы хотите поменять:</label>
                    <input type="text" name="give" placeholder="Например: Книга 'Война и мир'" required>
                </div>
                
                <div class="form-group">
                    <label>✅ Что вы хотите получить:</label>
                    <input type="text" name="get" placeholder="Например: Набор для рисования" required>
                </div>
                
                <div class="form-group">
                    <label>📞 Контакты для связи:</label>
                    <input type="text" name="contact" placeholder="Телефон, email или социальная сеть" required>
                </div>

                <button type="submit">📤 Опубликовать объявление</button>
            </form>
            
            <a href="/" class="back-link">⬅ Назад на главную</a>
        </div>
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
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Объявление добавлено</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px;
            }}
            .container {{
                max-width: 600px; margin: 0 auto; background: white; padding: 30px;
                border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
            }}
            .success-icon {{ font-size: 4em; margin-bottom: 20px; }}
            h2 {{ color: #27ae60; margin-bottom: 20px; }}
            .offer-details {{
                background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;
                text-align: left; border-left: 4px solid #27ae60;
            }}
            .btn {{
                display: inline-block; padding: 12px 25px; margin: 10px; background: #3498db;
                color: white; text-decoration: none; border-radius: 8px; font-weight: bold;
                transition: background 0.3s;
            }}
            .btn:hover {{ background: #2980b9; }}
            .back-link {{ 
                display: block; margin-top: 20px; color: #7f8c8d; text-decoration: none;
            }}
            .back-link:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✅</div>
            <h2>Ваше объявление успешно добавлено!</h2>
            
            <div class="offer-details">
                <p><b>🎁 Отдаёте:</b> {give}</p>
                <p><b>✅ Получаете:</b> {get}</p>
                <p><b>📞 Ваши контакты:</b> {contact}</p>
            </div>
            
            <div>
                <a href="/offer" class="btn">📋 Посмотреть все объявления</a>
                <a href="/addoffer" class="btn" style="background: #27ae60;">➕ Добавить ещё</a>
            </div>
            
            <a href="/" class="back-link">⬅ На главную</a>
        </div>
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
        content = """
        <div style="text-align: center; padding: 40px; color: #7f8c8d;">
            <div style="font-size: 4em; margin-bottom: 20px;">😔</div>
            <h3>Ничего не найдено</h3>
            <p>Попробуйте изменить поисковый запрос</p>
        </div>
        """
    else:
        content = f"<h3>🔍 Найдено объявлений: {len(filtered_offers)}</h3>"
        for offer in filtered_offers:
            content += f"""
            <div style='
                border: 2px solid #e0e0e0; padding: 20px; margin: 15px 0; border-radius: 10px;
                background: white; transition: transform 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            ' onmouseover="this.style.transform='translateY(-2px)'" 
            onmouseout="this.style.transform='translateY(0)'">
                <p style='margin: 8px 0; font-size: 1.1em;'><b>🎁 Отдаёт:</b> {offer['give']}</p>
                <p style='margin: 8px 0; font-size: 1.1em;'><b>✅ Хочет получить:</b> {offer['get']}</p>
                <p style='margin: 8px 0; color: #3498db;'><b>📞 Контакт:</b> {offer['contact']}</p>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Все объявления</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px;
            }}
            .container {{
                max-width: 800px; margin: 0 auto; background: white; padding: 30px;
                border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h2 {{ color: #2c3e50; margin-bottom: 20px; text-align: center; }}
            .search-form {{
                display: flex; gap: 10px; margin: 20px 0; background: #f8f9fa;
                padding: 20px; border-radius: 10px;
            }}
            .search-form input {{
                flex: 1; padding: 12px; border: 2px solid #bdc3c7; border-radius: 8px;
                font-size: 16px;
            }}
            .search-form button {{
                background: #3498db; color: white; padding: 12px 25px; border: none;
                border-radius: 8px; cursor: pointer; font-weight: bold;
            }}
            .search-form button:hover {{ background: #2980b9; }}
            .btn {{
                display: inline-block; padding: 12px 25px; background: #27ae60; color: white;
                text-decoration: none; border-radius: 8px; font-weight: bold; margin: 10px 5px;
                transition: background 0.3s;
            }}
            .btn:hover {{ background: #219a52; }}
            .nav-links {{ text-align: center; margin-top: 30px; }}
            .back-link {{ 
                display: inline-block; margin-top: 15px; color: #7f8c8d; text-decoration: none;
            }}
            .back-link:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📋 Все предложения пользователей</h2>

            <form method="get" action="/offer" class="search-form">
                <input type="text" name="q" placeholder="🔍 Поиск по объявлениям..." value="{q or ''}">
                <button type="submit">Найти</button>
            </form>

            {content}
            
            <div class="nav-links">
                <a href="/addoffer" class="btn">➕ Добавить новое объявление</a>
                <a href="/" class="btn" style="background: #95a5a6;">🏠 На главную</a>
                <br>
                <a href="/profile" class="back-link">👤 Перейти в профиль</a>
            </div>
        </div>
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
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)