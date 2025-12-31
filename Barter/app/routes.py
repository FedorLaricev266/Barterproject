# routes.py
from fastapi import FastAPI, Form, Request, UploadFile, File, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional, Dict, Any
import traceback

from database import db
from services import (
    UserService, OfferService, RatingService, 
    ExchangeService, AuthService, FileService, MessageService
)

# Инициализация сервисов
user_service = UserService()
offer_service = OfferService()
rating_service = RatingService()
exchange_service = ExchangeService()
auth_service = AuthService()
file_service = FileService()
message_service = MessageService()

# Конфигурация
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads", "offers")
AVATAR_DIR = os.path.join(STATIC_DIR, "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

# Создание приложения
def create_app() -> FastAPI:
    app = FastAPI(title="Swap Space - Платформа для обменов")
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    
    # ================================
    # Вспомогательные функции
    # ================================
    def get_current_user(request: Request):
        """Получить текущего пользователя из cookies"""
        token = request.cookies.get("session")
        if not token:
            return None
        
        user_id = auth_service.verify_token(token)
        if not user_id:
            return None
        
        return user_service.get_user_by_id(user_id)
    
    def get_template_context(request: Request, additional_context: dict = None):
        """Получить базовый контекст для всех шаблонов"""
        user = get_current_user(request)
        context = {"request": request, "user": user}
        
        if user:
            # Добавляем счетчик непрочитанных сообщений
            try:
                context["unread_messages_count"] = message_service.get_unread_count(user["id"])
            except:
                context["unread_messages_count"] = 0
        
        if additional_context:
            context.update(additional_context)
        
        return context
    
    # ================================
    # Главная страница
    # ================================
    
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Главная страница"""
        context = get_template_context(request)
        return templates.TemplateResponse("home.html", context)
    
    # ================================
    # Страница с объявлениями
    # ================================
    
    @app.get("/offer", response_class=HTMLResponse)
    async def offer_list(request: Request):
        """Список объявлений с фильтрами"""
        category = request.query_params.get("category", "")
        city = request.query_params.get("city", "")
        search = request.query_params.get("search", "")
        
        offers = offer_service.get_all_offers(category, city, search)
        
        # Добавляем рейтинг к каждому пользователю
        for offer in offers:
            if offer.get("user_id"):
                rating_stats = rating_service.get_user_rating_stats(offer["user_id"])
                offer["user_rating"] = rating_stats["avg_rating"]
                offer["total_ratings"] = rating_stats["total_ratings"]
        
        context = get_template_context(request, {
            "offers": offers,
            "current_category": category,
            "current_city": city,
            "current_search": search,
            "offers_count": len(offers),
        })
        
        return templates.TemplateResponse("offer_list.html", context)
    
    @app.get("/offer/{id}", response_class=HTMLResponse)
    async def offercard(request: Request, id: int):
        """Страница объявления"""
        try:
            offer = offer_service.get_offer_by_id(id)
            
            if not offer:
                return templates.TemplateResponse("404.html", get_template_context(request))
            
            # Получаем рейтинг пользователя, который создал объявление
            rating_stats = rating_service.get_user_rating_stats(offer["user_id"])
            
            # Проверяем, может ли текущий пользователь отправить сообщение
            current_user = get_current_user(request)
            can_message = current_user and current_user["id"] != offer["user_id"]
            
            context = get_template_context(request, {
                "offer": offer,
                "user_rating": rating_stats["avg_rating"],
                "total_ratings": rating_stats["total_ratings"],
                "can_message": can_message,
                "current_user": current_user
            })
            
            return templates.TemplateResponse("offercard.html", context)
            
        except Exception as e:
            return templates.TemplateResponse("error.html", get_template_context(request, {
                "error": f"Ошибка загрузки объявления: {str(e)}"
            }))
    
    # ================================
    # Добавление и управление объявлениями
    # ================================
    
    @app.get("/addoffer", response_class=HTMLResponse)
    async def addoffer_form(request: Request):
        """Форма добавления объявления"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        context = get_template_context(request)
        return templates.TemplateResponse("addoffer.html", context)
    
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
        """Обработка формы добавления объявления"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        image_url = None
        if image and image.filename:
            filename = file_service.save_uploaded_file(image, UPLOAD_DIR, "offer")
            image_url = f"/static/uploads/offers/{filename}"
        
        offer_service.create_offer(
            user["id"], give, get, contact, category, city, district, image_url
        )
        
        return RedirectResponse("/profile", status_code=303)
    
    @app.post("/delete_offer/{offer_id}")
    async def delete_offer(offer_id: int, request: Request):
        """Удаление объявления"""
        user = get_current_user(request)
        if not user:
            return JSONResponse(
                {"success": False, "message": "Авторизуйтесь"}, 
                status_code=401
            )
        
        try:
            # Проверяем, существует ли объявление
            offer = offer_service.get_offer_by_id(offer_id)
            if not offer or int(offer["user_id"]) != int(user["id"]):
                return JSONResponse(
                    {"success": False, "message": "Объявление не найдено или нет прав"}, 
                    status_code=404
                )
            
            # Удаляем изображение, если оно есть
            if offer.get("image_url"):
                try:
                    image_path = os.path.join(BASE_DIR, offer["image_url"].lstrip("/"))
                    file_service.delete_file(image_path)
                except Exception as e:
                    print(f"Ошибка при удалении изображения: {e}")
            
            # Деактивируем объявление
            success = offer_service.deactivate_offer(offer_id, user["id"])
            
            if success:
                return JSONResponse(
                    {"success": True, "message": "Объявление успешно удалено"}
                )
            else:
                return JSONResponse(
                    {"success": False, "message": "Ошибка при удалении"}, 
                    status_code=500
                )
                
        except Exception as e:
            print(f"Ошибка удаления объявления: {e}")
            traceback.print_exc()
            return JSONResponse(
                {"success": False, "message": "Ошибка на сервере"}, 
                status_code=500
            )
    
    # ================================
    # Профиль пользователя
    # ================================
    
    @app.get("/profile", response_class=HTMLResponse)
    async def profile(request: Request):
        """Личный профиль пользователя"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        # Получаем активные объявления
        offers = offer_service.get_user_offers(user["id"])
        
        # Получаем количество всех активных объявлений пользователя
        offers_count = offer_service.count_user_offers(user["id"])
        
        # Получаем количество успешных обменов
        successful_exchanges = exchange_service.count_successful_exchanges(user["id"])
        
        # Получаем рейтинг
        rating_stats = rating_service.get_user_rating_stats(user["id"])
        
        # Форматируем дату регистрации
        registration_date = user.get("registration_date")
        if registration_date and hasattr(registration_date, 'strftime'):
            registration_date_str = registration_date.strftime("%d.%m.%Y")
        else:
            registration_date_str = "Неизвестно"
        
        context = get_template_context(request, {
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
            "offers": offers,
            "user_id": user["id"],
        })
        
        return templates.TemplateResponse("profile.html", context)
    
    @app.get("/edit_profile", response_class=HTMLResponse)
    async def edit_profile_form(request: Request):
        """Форма редактирования профиля"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        context = get_template_context(request, {"user": user})
        return templates.TemplateResponse("edit_profile.html", context)
    
    @app.post("/edit_profile", response_class=HTMLResponse)
    async def edit_profile_submit(
        request: Request,
        full_name: str = Form(None),
        phone: str = Form(None),
        about_me: str = Form(None),
        avatar: UploadFile = File(None),
    ):
        """Обработка формы редактирования профиля"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        avatar_url = user.get("avatar_url")
        
        # Загрузка аватара
        if avatar and avatar.filename:
            filename = file_service.save_uploaded_file(
                avatar, AVATAR_DIR, "avatar", user["id"]
            )
            
            # Удаляем старый аватар, если он есть
            if avatar_url:
                old_filename = os.path.basename(avatar_url)
                old_path = os.path.join(AVATAR_DIR, old_filename)
                file_service.delete_file(old_path)
            
            avatar_url = f"/static/uploads/avatars/{filename}"
        
        # Обновление данных пользователя
        user_service.update_user_profile(
            user["id"], full_name, phone, about_me, avatar_url
        )
        
        return RedirectResponse("/profile", status_code=303)
    
    # ================================
    # Публичный профиль
    # ================================
    
    @app.get("/user/{user_id}", response_class=HTMLResponse)
    async def public_profile(request: Request, user_id: int):
        """Публичный профиль пользователя"""
        current_user = get_current_user(request)
        
        # Получаем информацию о пользователе
        user = user_service.get_user_by_id(user_id)
        if not user:
            return templates.TemplateResponse("404.html", get_template_context(request))
        
        # Получаем активные объявления пользователя
        offers = offer_service.get_user_offers(user_id, limit=10)
        
        # Статистика пользователя
        offers_count = offer_service.count_user_offers(user_id)
        successful_exchanges = exchange_service.count_successful_exchanges(user_id)
        
        # Получаем рейтинг пользователя
        rating_stats = rating_service.get_user_rating_stats(user_id)
        
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
        recent_reviews = rating_service.get_recent_reviews(user_id)
        
        # Проверяем, можно ли отправить сообщение
        can_message = current_user and current_user["id"] != user_id
        
        context = get_template_context(request, {
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
            "can_message": can_message,
        })
        
        return templates.TemplateResponse("public_profile.html", context)
    
    @app.get("/user/", response_class=HTMLResponse)
    async def user_redirect(request: Request):
        """Перенаправление с /user/ на профиль текущего пользователя"""
        user = get_current_user(request)
        if user:
            return RedirectResponse(f"/user/{user['id']}", status_code=303)
        else:
            return RedirectResponse("/", status_code=303)
    
    # ================================
    # Рейтинг пользователей
    # ================================
    
    @app.post("/rate_user/{target_user_id}")
    async def rate_user(
        target_user_id: int,
        request: Request,
        rating: int = Form(...),
        comment: Optional[str] = Form(None)
    ):
        """Оценка пользователя"""
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
            success = rating_service.add_or_update_rating(
                current_user["id"], target_user_id, rating, comment
            )
            
            if not success:
                return JSONResponse(
                    {"success": False, "message": "Пользователь не найден"}, 
                    status_code=404
                )
            
            # Получаем обновленную статистику
            new_stats = rating_service.get_user_rating_stats(target_user_id)
            
            return JSONResponse({
                "success": True,
                "message": "Оценка добавлена" if not rating_service.has_user_rated(current_user["id"], target_user_id) else "Оценка обновлена",
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
    # МЕССЕНДЖЕР
    # ================================
    
    @app.get("/messages", response_class=HTMLResponse)
    async def messages_list(request: Request):
        """Список диалогов"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        dialogs = message_service.get_user_dialogs(user["id"])
        unread_count = message_service.get_unread_count(user["id"])
        
        context = get_template_context(request, {
            "dialogs": dialogs,
            "unread_count": unread_count,
            "user": user
        })
        
        return templates.TemplateResponse("messages_list.html", context)
    
    @app.get("/messages/{other_user_id}", response_class=HTMLResponse)
    async def conversation_detail(
        request: Request, 
        other_user_id: int,
        page: int = Query(1, ge=1)
    ):
        """Диалог с конкретным пользователем"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        # Проверяем существование собеседника
        other_user = user_service.get_user_by_id(other_user_id)
        if not other_user:
            return templates.TemplateResponse("404.html", get_template_context(request))
        
        # Получаем сообщения
        messages = message_service.get_conversation(user["id"], other_user_id)
        
        # Получаем информацию о диалоге
        total_messages_result = db.execute_query(
            """SELECT COUNT(*) as count FROM messages 
               WHERE (sender_id = %s AND recipient_id = %s)
                  OR (sender_id = %s AND recipient_id = %s)""",
            (user["id"], other_user_id, other_user_id, user["id"]),
            fetch=True
        )
        
        total_messages = total_messages_result[0]["count"] if total_messages_result else 0
        
        context = get_template_context(request, {
            "messages": messages,
            "other_user": other_user,
            "current_user": user,
            "page": page,
            "total_messages": total_messages,
        })
        
        return templates.TemplateResponse("conversation.html", context)
    
    @app.post("/messages/{other_user_id}/send")
    async def send_message(
        request: Request,
        other_user_id: int,
        message: str = Form(...),
        offer_id: Optional[int] = Form(None)
    ):
        """Отправить сообщение"""
        user = get_current_user(request)
        if not user:
            return JSONResponse(
                {"success": False, "message": "Требуется авторизация"},
                status_code=401
            )
        
        if not message.strip():
            return JSONResponse(
                {"success": False, "message": "Сообщение не может быть пустым"},
                status_code=400
            )
        
        try:
            success = message_service.send_message(
                user["id"], other_user_id, message, offer_id
            )
            
            if success:
                return JSONResponse({
                    "success": True,
                    "message": "Сообщение отправлено"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "message": "Ошибка отправки сообщения"
                }, status_code=500)
                
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return JSONResponse({
                "success": False,
                "message": f"Ошибка сервера: {str(e)}"
            }, status_code=500)
    
    @app.get("/messages/{other_user_id}/new")
    async def get_new_messages(
        request: Request,
        other_user_id: int,
        last_message_id: int = Query(0, ge=0)
    ):
        """Получить новые сообщения (для AJAX)"""
        user = get_current_user(request)
        if not user:
            return JSONResponse({"success": False}, status_code=401)
        
        # Получаем сообщения после last_message_id
        query = """
            SELECT 
                m.*,
                u.username as sender_username,
                u.avatar_url as sender_avatar
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE ((m.sender_id = %s AND m.recipient_id = %s)
               OR (m.sender_id = %s AND m.recipient_id = %s))
               AND m.id > %s
            ORDER BY m.created_at ASC
        """
        
        new_messages = db.execute_query(
            query,
            (user["id"], other_user_id, other_user_id, user["id"], last_message_id),
            fetch=True
        ) or []
        
        # Помечаем как прочитанные
        if new_messages:
            message_ids = [msg["id"] for msg in new_messages]
            message_service.mark_as_read(message_ids, user["id"])
        
        return JSONResponse({
            "success": True,
            "messages": new_messages,
            "count": len(new_messages)
        })
    
    @app.post("/messages/delete/{message_id}")
    async def delete_message_route(
        request: Request,
        message_id: int
    ):
        """Удалить сообщение"""
        user = get_current_user(request)
        if not user:
            return JSONResponse(
                {"success": False, "message": "Требуется авторизация"},
                status_code=401
            )
        
        success = message_service.delete_message(message_id, user["id"])
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Сообщение удалено"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Не удалось удалить сообщение"
            }, status_code=403)
    
    @app.post("/messages/clear/{other_user_id}")
    async def clear_conversation(
        request: Request,
        other_user_id: int
    ):
        """Очистить переписку с пользователем"""
        user = get_current_user(request)
        if not user:
            return JSONResponse(
                {"success": False, "message": "Требуется авторизация"},
                status_code=401
            )
        
        try:
            db.execute_query(
                """DELETE FROM messages 
                   WHERE (sender_id = %s AND recipient_id = %s)
                      OR (sender_id = %s AND recipient_id = %s)""",
                (user["id"], other_user_id, other_user_id, user["id"]),
            )
            
            return JSONResponse({
                "success": True,
                "message": "Переписка очищена"
            })
        except Exception as e:
            return JSONResponse({
                "success": False,
                "message": f"Ошибка: {str(e)}"
            }, status_code=500)
    
    @app.get("/api/unread_count")
    async def get_unread_count_api(request: Request):
        """API для получения количества непрочитанных сообщений"""
        user = get_current_user(request)
        if not user:
            return JSONResponse({"count": 0})
        
        count = message_service.get_unread_count(user["id"])
        return JSONResponse({"count": count})
    
    @app.post("/start_conversation/{user_id}")
    async def start_conversation(
        request: Request,
        user_id: int,
        message: str = Form(...),
        offer_id: Optional[int] = Form(None)
    ):
        """Начать новую переписку с пользователем"""
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(
                {"success": False, "message": "Требуется авторизация"},
                status_code=401
            )
        
        if current_user["id"] == user_id:
            return JSONResponse(
                {"success": False, "message": "Нельзя написать самому себе"},
                status_code=400
            )
        
        success = message_service.send_message(
            current_user["id"], user_id, message, offer_id
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Сообщение отправлено",
                "redirect_url": f"/messages/{user_id}"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Ошибка отправки сообщения"
            }, status_code=500)
    
    # ================================
    # Аутентификация
    # ================================
    
    @app.get("/register", response_class=HTMLResponse)
    async def register_page(request: Request):
        """Страница регистрации"""
        context = get_template_context(request)
        return templates.TemplateResponse("auth.html", context)
    
    @app.post("/register")
    async def register_user(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        email: str = Form(...),
    ):
        """Регистрация пользователя"""
        # Проверяем, существует ли пользователь
        if auth_service.check_user_exists(username, email):
            context = get_template_context(request, {
                "error": "Пользователь с таким именем или email уже существует"
            })
            return templates.TemplateResponse("auth.html", context)
        
        user_service.create_user(username, password, email)
        context = get_template_context(request)
        return templates.TemplateResponse("register_success.html", context)
    
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Страница входа"""
        context = get_template_context(request)
        return templates.TemplateResponse("auth.html", context)
    
    @app.post("/login")
    async def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
    ):
        """Авторизация пользователя"""
        user = user_service.check_credentials(username, password)
        if not user:
            context = get_template_context(request, {
                "error": "Неверный логин или пароль"
            })
            return templates.TemplateResponse("auth.html", context)
        
        token = auth_service.generate_token(user["id"])
        response = RedirectResponse("/profile", status_code=303)
        response.set_cookie("session", token, max_age=3600 * 24 * 30, httponly=True)
        return response
    
    @app.post("/logout")
    async def logout():
        """Выход из системы"""
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("session")
        return response
    
    # ================================
    # Мини-игра
    # ================================
    
    @app.get("/minigame", response_class=HTMLResponse)
    async def minigame(request: Request):
        """Мини-игра"""
        context = get_template_context(request)
        return templates.TemplateResponse("minigame.html", context)
    
    # ================================
    # API для фронтенда
    # ================================
    
    @app.get("/api/search_users")
    async def search_users(
        request: Request,
        q: str = Query(..., min_length=2),
        limit: int = Query(10, ge=1, le=50)
    ):
        """Поиск пользователей для мессенджера"""
        user = get_current_user(request)
        if not user:
            return JSONResponse({"users": []})
        
        users = db.execute_query(
            """SELECT id, username, avatar_url, full_name 
               FROM users 
               WHERE username LIKE %s 
                  OR full_name LIKE %s 
               AND id != %s
               LIMIT %s""",
            (f"%{q}%", f"%{q}%", user["id"], limit),
            fetch=True
        ) or []
        
        return JSONResponse({"users": users})
    
    # ================================
    # Статические страницы
    # ================================
    
    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        """Страница "О нас" """
        context = get_template_context(request)
        return templates.TemplateResponse("about.html", context)
    
    @app.get("/help", response_class=HTMLResponse)
    async def help_page(request: Request):
        """Страница помощи"""
        context = get_template_context(request)
        return templates.TemplateResponse("help.html", context)
    
    @app.get("/rules", response_class=HTMLResponse)
    async def rules(request: Request):
        """Правила сайта"""
        context = get_template_context(request)
        return templates.TemplateResponse("rules.html", context)
    
    # ================================
    # Обработчики ошибок
    # ================================
    
    @app.exception_handler(404)
    async def not_found(request, exc):
        return templates.TemplateResponse("404.html", get_template_context(request))
    
    @app.exception_handler(500)
    async def server_error(request, exc):
        traceback.print_exc()
        return templates.TemplateResponse("error.html", get_template_context(request))
    
    @app.exception_handler(401)
    async def unauthorized(request, exc):
        return RedirectResponse("/login", status_code=303)
    
    @app.exception_handler(403)
    async def forbidden(request, exc):
        return templates.TemplateResponse("403.html", get_template_context(request))
    
    return app