from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
import bcrypt
import os
import shutil
from typing import Optional

from database import db

# ================================
# Конфигурация
# ================================
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads", "offers")
AVATAR_DIR = os.path.join(STATIC_DIR, "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SECRET_KEY = "super_secret_key_123"
serializer = URLSafeTimedSerializer(SECRET_KEY)


# ================================
# Пользователь
# ================================
def get_current_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        user_id = serializer.loads(token, max_age=3600 * 24 * 30)
    except Exception:
        return None
    user_data = db.execute_query(
        "SELECT * FROM users WHERE id = %s", (user_id,), fetch=True
    )
    return user_data[0] if user_data else None


# ================================
# Функции для работы с рейтингом
# ================================
def get_user_rating_stats(user_id: int):
    """Получить статистику рейтинга пользователя"""
    rating_query = """
        SELECT 
            COALESCE(AVG(rating), 0) as avg_rating,
            COALESCE(COUNT(*), 0) as total_ratings,
            COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
            COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
            COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
            COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
            COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
        FROM ratings 
        WHERE target_user_id = %s
    """
    stats = db.execute_query(rating_query, (user_id,), fetch=True)

    if stats and stats[0]:
        total_ratings = int(stats[0]["total_ratings"])

        if total_ratings > 0:
            avg_rating = float(stats[0]["avg_rating"])
            distribution = {
                5: (int(stats[0]["five_star"]) / total_ratings) * 100,
                4: (int(stats[0]["four_star"]) / total_ratings) * 100,
                3: (int(stats[0]["three_star"]) / total_ratings) * 100,
                2: (int(stats[0]["two_star"]) / total_ratings) * 100,
                1: (int(stats[0]["one_star"]) / total_ratings) * 100,
            }
        else:
            avg_rating = 0
            distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

        return {
            "avg_rating": round(avg_rating, 1),
            "total_ratings": total_ratings,
            "distribution": distribution
        }

    return {
        "avg_rating": 0,
        "total_ratings": 0,
        "distribution": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    }


def has_user_rated(rater_id: int, target_user_id: int) -> bool:
    """Проверить, ставил ли пользователь оценку другому пользователю"""
    query = "SELECT id FROM ratings WHERE rater_user_id = %s AND target_user_id = %s"
    result = db.execute_query(query, (rater_id, target_user_id), fetch=True)
    return len(result) > 0


def get_user_rating(rater_id: int, target_user_id: int) -> Optional[int]:
    """Получить оценку, которую поставил пользователь"""
    query = "SELECT rating FROM ratings WHERE rater_user_id = %s AND target_user_id = %s"
    result = db.execute_query(query, (rater_id, target_user_id), fetch=True)
    return result[0]["rating"] if result else None


# ================================
# Главная
# ================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("home.html", {"request": request, "user": user})


# ================================
# Список всех объявлений
# ================================
@app.get("/offer", response_class=HTMLResponse)
async def offer_list(request: Request):
    category = request.query_params.get("category", "")
    city = request.query_params.get("city", "")
    search = request.query_params.get("search", "")

    query = """
        SELECT o.*, u.username, u.avatar_url
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

    offers = db.execute_query(query, params, fetch=True) or []

    # Добавляем рейтинг к каждому пользователю
    for offer in offers:
        if offer.get("user_id"):
            rating_stats = get_user_rating_stats(offer["user_id"])
            offer["user_rating"] = rating_stats["avg_rating"]
            offer["total_ratings"] = rating_stats["total_ratings"]

    return templates.TemplateResponse(
        "offer_list.html",
        {
            "request": request,
            "offers": offers,
            "current_category": category,
            "current_city": city,
            "current_search": search,
            "offers_count": len(offers),
        },
    )


# ================================
# Профиль пользователя (публичный)
# ================================
@app.get("/user/{user_id}", response_class=HTMLResponse)
async def public_profile(request: Request, user_id: int):
    current_user = get_current_user(request)

    # Получаем информацию о пользователе
    user_data = db.execute_query(
        """SELECT id, username, email, full_name, phone, 
           registration_date, avatar_url, about_me 
           FROM users WHERE id = %s""",
        (user_id,),
        fetch=True,
    )

    if not user_data:
        return templates.TemplateResponse("404.html", {"request": request})

    user = user_data[0]

    # Получаем активные объявления пользователя
    offers = db.execute_query(
        """SELECT id, give, `get`, image_url, created_at 
           FROM offers WHERE user_id = %s AND is_active = TRUE 
           ORDER BY created_at DESC LIMIT 10""",
        (user_id,),
        fetch=True,
    ) or []

    # Статистика пользователя
    offers_result = db.execute_query(
        "SELECT COUNT(*) AS count FROM offers WHERE user_id = %s AND is_active = TRUE",
        (user_id,),
        fetch=True,
    )
    offers_count = offers_result[0]["count"] if offers_result else 0

    exchanges_result = db.execute_query(
        """SELECT COUNT(*) AS count FROM exchanges 
           WHERE (offer1_user_id = %s OR offer2_user_id = %s) 
           AND status = 'completed'""",
        (user_id, user_id),
        fetch=True,
    )
    successful_exchanges = exchanges_result[0]["count"] if exchanges_result else 0

    # Получаем рейтинг пользователя
    rating_stats = get_user_rating_stats(user_id)

    # Проверяем, ставил ли текущий пользователь оценку
    has_rated = False
    user_rating = None
    comment = None
    if current_user:
        rating_result = db.execute_query(
            "SELECT rating, comment FROM ratings WHERE rater_user_id = %s AND target_user_id = %s",
            (current_user["id"], user_id),
            fetch=True,
        )
        if rating_result:
            has_rated = True
            user_rating = rating_result[0]["rating"]
            comment = rating_result[0].get("comment")

    # Получаем последние отзывы
    recent_reviews = db.execute_query(
        """SELECT r.*, u.username as rater_username, u.avatar_url as rater_avatar
           FROM ratings r
           JOIN users u ON r.rater_user_id = u.id
           WHERE r.target_user_id = %s
           ORDER BY r.created_at DESC
           LIMIT 5""",
        (user_id,),
        fetch=True,
    ) or []

    context = {
        "request": request,
        "profile_user": user,
        "current_user": current_user,
        "offers": offers,
        "offers_count": offers_count,
        "successful_exchanges": successful_exchanges,
        "rating_stats": rating_stats,
        "has_rated": has_rated,
        "user_rating": user_rating,
        "comment": comment,
        "recent_reviews": recent_reviews,
    }

    return templates.TemplateResponse("public_profile.html", context)


# ================================
# Добавление/изменение оценки
# ================================
@app.post("/rate_user/{target_user_id}")
async def rate_user(
    target_user_id: int,
    request: Request,
    rating: int = Form(...),
    comment: Optional[str] = Form(None)
):
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse(
            {"success": False, "message": "Требуется авторизация"}, 
            status_code=401
        )

    if current_user["id"] == target_user_id:
        return JSONResponse(
            {"success": False, "message": "Нельзя оценивать себя"}, 
            status_code=400
        )

    if rating < 1 or rating > 5:
        return JSONResponse(
            {"success": False, "message": "Оценка должна быть от 1 до 5"}, 
            status_code=400
        )

    try:
        # Проверяем существование целевого пользователя
        target_user = db.execute_query(
            "SELECT id FROM users WHERE id = %s",
            (target_user_id,),
            fetch=True,
        )

        if not target_user:
            return JSONResponse(
                {"success": False, "message": "Пользователь не найден"}, 
                status_code=404
            )

        # Проверяем, есть ли уже оценка от этого пользователя
        existing_rating = db.execute_query(
            "SELECT id FROM ratings WHERE rater_user_id = %s AND target_user_id = %s",
            (current_user["id"], target_user_id),
            fetch=True,
        )

        if existing_rating:
            # Обновляем существующую оценку
            db.execute_query(
                """UPDATE ratings 
                   SET rating = %s, comment = %s, created_at = NOW() 
                   WHERE id = %s""",
                (rating, comment, existing_rating[0]["id"]),
            )
            message = "Оценка обновлена"
        else:
            # Добавляем новую оценку
            db.execute_query(
                """INSERT INTO ratings (rater_user_id, target_user_id, rating, comment, created_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (current_user["id"], target_user_id, rating, comment),
            )
            message = "Оценка добавлена"

        # Получаем обновленную статистику
        new_stats = get_user_rating_stats(target_user_id)

        return JSONResponse({
            "success": True,
            "message": message,
            "avg_rating": new_stats["avg_rating"],
            "total_ratings": new_stats["total_ratings"]
        })

    except Exception as e:
        print(f"Ошибка при оценке пользователя: {e}")
        return JSONResponse(
            {"success": False, "message": "Ошибка сервера"}, 
            status_code=500
        )


# ================================
# Профиль текущего пользователя
# ================================
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Получаем активные объявления
    offers = db.execute_query(
        "SELECT id, give, `get`, image_url FROM offers WHERE user_id = %s AND is_active = TRUE",
        (user["id"],),
        fetch=True,
    )
    
    # Отладка
    print(f"=== DEBUG PROFILE ===")
    print(f"User ID: {user['id']}")
    print(f"Username: {user['username']}")
    print(f"Found offers: {len(offers) if offers else 0}")
    
    if not offers:
        offers = []
        print("DEBUG: Offers list is empty or None")
    else:
        print("DEBUG: Offers found:")
        for offer in offers:
            print(f"  - ID: {offer['id']}, Give: {offer['give']}, Get: {offer['get']}")

    # Получаем количество всех активных объявлений пользователя
    offers_result = db.execute_query(
        "SELECT COUNT(*) AS count FROM offers WHERE user_id = %s AND is_active = TRUE",
        (user["id"],),
        fetch=True,
    )
    offers_count = offers_result[0]["count"] if offers_result else 0
    print(f"DEBUG: Total active offers in DB: {offers_count}")

    # Получаем количество успешных обменов
    exchanges_result = db.execute_query(
        """SELECT COUNT(*) as count FROM exchanges 
           WHERE status = 'completed' 
           AND (offer1_user_id = %s OR offer2_user_id = %s)""",
        (user["id"], user["id"]),
        fetch=True,
    )
    successful_exchanges = exchanges_result[0]["count"] if exchanges_result else 0
    print(f"DEBUG: Successful exchanges: {successful_exchanges}")

    # Получаем рейтинг
    rating_stats = get_user_rating_stats(user["id"])
    print(f"DEBUG: Rating stats: {rating_stats}")

    # Форматируем дату регистрации
    registration_date = user.get("registration_date")
    if registration_date and hasattr(registration_date, 'strftime'):
        registration_date_str = registration_date.strftime("%d.%m.%Y")
    else:
        registration_date_str = "Неизвестно"

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "username": user["username"],
            "full_name": user.get("full_name", ""),
            "email": user["email"],
            "phone": user.get("phone", ""),
            "avatar_url": user.get("avatar_url", ""),
            "about_me": user.get("about_me", ""),
            "registration_date": registration_date_str,
            "offers_count": offers_count,
            "successful_exchanges": successful_exchanges,
            "rating_stats": rating_stats,
            "offers": offers,  # Исправлено: передаем как offers, а не active_offers
            "user_id": user["id"],
        },
    )


# ================================
# Редактирование профиля
# ================================
@app.get("/edit_profile", response_class=HTMLResponse)
async def edit_profile_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "edit_profile.html", 
        {"request": request, "user": user}
    )


@app.post("/edit_profile", response_class=HTMLResponse)
async def edit_profile_submit(
    request: Request,
    full_name: str = Form(None),
    phone: str = Form(None),
    about_me: str = Form(None),
    avatar: UploadFile = File(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    avatar_url = user.get("avatar_url")

    # Загрузка аватара
    if avatar and avatar.filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(avatar.filename)[1]
        filename = f"avatar_{user['id']}_{ts}{ext}"
        file_path = os.path.join(AVATAR_DIR, filename)

        # Удаляем старый аватар, если он есть
        if avatar_url:
            old_filename = os.path.basename(avatar_url)
            old_path = os.path.join(AVATAR_DIR, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
        avatar_url = f"/static/uploads/avatars/{filename}"

    # Обновление данных пользователя
    db.execute_query(
        """UPDATE users 
           SET full_name = %s, phone = %s, about_me = %s, avatar_url = %s 
           WHERE id = %s""",
        (full_name, phone, about_me, avatar_url, user["id"]),
    )

    return RedirectResponse("/profile", status_code=303)


# ================================
# Добавление объявления
# ================================
@app.get("/addoffer", response_class=HTMLResponse)
async def addoffer_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
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
    image: UploadFile = File(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    image_path = None
    if image and image.filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(image.filename)[1]
        filename = f"offer_{ts}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = f"/static/uploads/offers/{filename}"

    db.execute_query(
        """INSERT INTO offers (user_id, give, `get`, contact, 
           category, city, district, image_url, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())""",
        (user["id"], give, get, contact, category, city, district, image_path),
    )

    return RedirectResponse("/profile", status_code=303)  # Редирект на профиль


# ================================
# Удаление объявления
# ================================
@app.post("/delete_offer/{offer_id}")
async def delete_offer(offer_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Авторизуйтесь"}, 
            status_code=401
        )

    try:
        # Проверяем, существует ли объявление и принадлежит ли текущему пользователю
        offer = db.execute_query(
            "SELECT id, user_id, image_url FROM offers WHERE id = %s AND is_active = TRUE",
            (offer_id,),
            fetch=True,
        )

        if not offer:
            return JSONResponse(
                {"success": False, "message": "Объявление не найдено или уже удалено"}, 
                status_code=404
            )

        if int(offer[0]["user_id"]) != int(user["id"]):
            return JSONResponse(
                {"success": False, "message": "Нет прав удалять это объявление"}, 
                status_code=403
            )

        # Удаляем изображение, если оно есть
        if offer[0].get("image_url"):
            try:
                image_path = os.path.join(BASE_DIR, offer[0]["image_url"].lstrip("/"))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Ошибка при удалении изображения: {e}")

        # Устанавливаем is_active = FALSE вместо физического удаления
        db.execute_query(
            "UPDATE offers SET is_active = FALSE WHERE id = %s", 
            (offer_id,)
        )
        
        return JSONResponse(
            {"success": True, "message": "Объявление успешно удалено"}
        )

    except Exception as e:
        print(f"Ошибка удаления объявления: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"success": False, "message": "Ошибка на сервере"}, 
            status_code=500
        )


# ================================
# Регистрация, логин, логаут
# ================================
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
):
    # Проверяем, существует ли пользователь
    existing_user = db.execute_query(
        "SELECT id FROM users WHERE username = %s OR email = %s",
        (username, email),
        fetch=True,
    )

    if existing_user:
        return templates.TemplateResponse("auth.html", {
            "request": request,
            "error": "Пользователь с таким именем или email уже существует"
        })

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.execute_query(
        """INSERT INTO users (username, password_hash, email, registration_date) 
           VALUES (%s, %s, %s, NOW())""",
        (username, hashed, email),
    )
    return templates.TemplateResponse("register_success.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.execute_query(
        "SELECT * FROM users WHERE username = %s", (username,), fetch=True
    )
    if not user or not bcrypt.checkpw(
        password.encode(), user[0]["password_hash"].encode()
    ):
        return templates.TemplateResponse(
            "auth.html", 
            {"request": request, "error": "Неверный логин или пароль"}
        )

    token = serializer.dumps(user[0]["id"])
    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie("session", token, max_age=3600 * 24 * 30, httponly=True)
    return response


@app.post("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session")
    return response


# ================================
# Детальная страница объявления
# ================================
@app.get("/offer/{id}", response_class=HTMLResponse)
async def offercard(request: Request, id: int):
    try:
        query = """
            SELECT o.*, u.username, u.email, u.phone, u.avatar_url
            FROM offers o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.is_active = TRUE
        """
        offer_data = db.execute_query(query, (id,), fetch=True)

        if not offer_data:
            return templates.TemplateResponse("404.html", {"request": request})

        offer = offer_data[0]

        # Получаем рейтинг пользователя, который создал объявление
        rating_stats = get_user_rating_stats(offer["user_id"])

        context = {
            "request": request,
            "offer": offer,
            "user_rating": rating_stats["avg_rating"],
            "total_ratings": rating_stats["total_ratings"]
        }
        return templates.TemplateResponse("offercard.html", context)

    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка загрузки объявления: {str(e)}"
        })


# ================================
# Реддирект для /user/ без ID
# ================================
@app.get("/user/", response_class=HTMLResponse)
async def user_redirect(request: Request):
    """Перенаправление с /user/ на профиль текущего пользователя"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(f"/user/{user['id']}", status_code=303)
    else:
        return RedirectResponse("/", status_code=303)


# ================================
# Обработчики ошибок
# ================================
@app.exception_handler(404)
async def not_found(request, exc):
    return templates.TemplateResponse("404.html", {"request": request})


@app.exception_handler(500)
async def server_error(request, exc):
    return templates.TemplateResponse("error.html", {"request": request})


# ================================
# Мини-игра
# ================================
@app.get("/minigame", response_class=HTMLResponse)
async def minigame(request: Request):
    return templates.TemplateResponse("minigame.html", {"request": request})


# ================================
# Запуск
# ================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)