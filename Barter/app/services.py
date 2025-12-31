# services.py
from datetime import datetime
import bcrypt
import os
import shutil
from typing import Optional, Dict, Any, List
from itsdangerous import URLSafeTimedSerializer
import json

from database import db

SECRET_KEY = "super_secret_key_123"
serializer = URLSafeTimedSerializer(SECRET_KEY)


class UserService:
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        user_data = db.execute_query(
            "SELECT * FROM users WHERE id = %s", (user_id,), fetch=True
        )
        return user_data[0] if user_data else None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по имени"""
        user_data = db.execute_query(
            "SELECT * FROM users WHERE username = %s", (username,), fetch=True
        )
        return user_data[0] if user_data else None

    @staticmethod
    def create_user(username: str, password: str, email: str) -> int:
        """Создать нового пользователя"""
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        result = db.execute_query(
            """INSERT INTO users (username, password_hash, email, registration_date) 
               VALUES (%s, %s, %s, NOW())""",
            (username, hashed, email),
        )
        return result

    @staticmethod
    def update_user_profile(
        user_id: int,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        about_me: Optional[str] = None,
        avatar_url: Optional[str] = None
    ):
        """Обновить профиль пользователя"""
        db.execute_query(
            """UPDATE users 
               SET full_name = %s, phone = %s, about_me = %s, avatar_url = %s 
               WHERE id = %s""",
            (full_name, phone, about_me, avatar_url, user_id),
        )

    @staticmethod
    def check_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Проверить логин и пароль"""
        user = db.execute_query(
            "SELECT * FROM users WHERE username = %s", (username,), fetch=True
        )
        if user and bcrypt.checkpw(
            password.encode(), user[0]["password_hash"].encode()
        ):
            return user[0]
        return None


class OfferService:
    @staticmethod
    def get_all_offers(
        category: str = "",
        city: str = "",
        search: str = ""
    ) -> List[Dict[str, Any]]:
        """Получить все активные объявления с фильтрами"""
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
        return db.execute_query(query, params, fetch=True) or []

    @staticmethod
    def get_offer_by_id(offer_id: int) -> Optional[Dict[str, Any]]:
        """Получить объявление по ID"""
        query = """
            SELECT o.*, u.username, u.email, u.phone, u.avatar_url
            FROM offers o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.is_active = TRUE
        """
        result = db.execute_query(query, (offer_id,), fetch=True)
        return result[0] if result else None

    @staticmethod
    def get_user_offers(user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Получить объявления пользователя"""
        query = """
            SELECT id, give, `get`, image_url, created_at 
            FROM offers 
            WHERE user_id = %s AND is_active = TRUE 
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        return db.execute_query(query, (user_id,), fetch=True) or []

    @staticmethod
    def create_offer(
        user_id: int,
        give: str,
        get: str,
        contact: str,
        category: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        image_url: Optional[str] = None
    ):
        """Создать новое объявление"""
        db.execute_query(
            """INSERT INTO offers (user_id, give, `get`, contact, 
               category, city, district, image_url, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())""",
            (user_id, give, get, contact, category, city, district, image_url),
        )

    @staticmethod
    def deactivate_offer(offer_id: int, user_id: int) -> bool:
        """Деактивировать объявление (удалить)"""
        # Проверяем, существует ли объявление и принадлежит ли пользователю
        offer = db.execute_query(
            "SELECT id FROM offers WHERE id = %s AND user_id = %s AND is_active = TRUE",
            (offer_id, user_id),
            fetch=True,
        )
        
        if not offer:
            return False
        
        db.execute_query(
            "UPDATE offers SET is_active = FALSE WHERE id = %s", 
            (offer_id,)
        )
        return True

    @staticmethod
    def count_user_offers(user_id: int) -> int:
        """Посчитать активные объявления пользователя"""
        result = db.execute_query(
            "SELECT COUNT(*) AS count FROM offers WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
            fetch=True,
        )
        return result[0]["count"] if result else 0


class RatingService:
    @staticmethod
    def get_user_rating_stats(user_id: int) -> Dict[str, Any]:
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

    @staticmethod
    def has_user_rated(rater_id: int, target_user_id: int) -> bool:
        """Проверить, ставил ли пользователь оценку другому пользователю"""
        query = "SELECT id FROM ratings WHERE rater_user_id = %s AND target_user_id = %s"
        result = db.execute_query(query, (rater_id, target_user_id), fetch=True)
        return len(result) > 0

    @staticmethod
    def get_user_rating(rater_id: int, target_user_id: int) -> Optional[int]:
        """Получить оценку, которую поставил пользователь"""
        query = "SELECT rating FROM ratings WHERE rater_user_id = %s AND target_user_id = %s"
        result = db.execute_query(query, (rater_id, target_user_id), fetch=True)
        return result[0]["rating"] if result else None

    @staticmethod
    def add_or_update_rating(
        rater_id: int,
        target_user_id: int,
        rating: int,
        comment: Optional[str] = None
    ) -> bool:
        """Добавить или обновить оценку пользователя"""
        # Проверяем существование целевого пользователя
        target_user = db.execute_query(
            "SELECT id FROM users WHERE id = %s",
            (target_user_id,),
            fetch=True,
        )
        
        if not target_user:
            return False

        # Проверяем, есть ли уже оценка от этого пользователя
        existing_rating = db.execute_query(
            "SELECT id FROM ratings WHERE rater_user_id = %s AND target_user_id = %s",
            (rater_id, target_user_id),
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
        else:
            # Добавляем новую оценку
            db.execute_query(
                """INSERT INTO ratings (rater_user_id, target_user_id, rating, comment, created_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (rater_id, target_user_id, rating, comment),
            )
        
        return True

    @staticmethod
    def get_recent_reviews(target_user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Получить последние отзывы о пользователе"""
        return db.execute_query(
            """SELECT r.*, u.username as rater_username, u.avatar_url as rater_avatar
               FROM ratings r
               JOIN users u ON r.rater_user_id = u.id
               WHERE r.target_user_id = %s
               ORDER BY r.created_at DESC
               LIMIT %s""",
            (target_user_id, limit),
            fetch=True,
        ) or []


class ExchangeService:
    @staticmethod
    def count_successful_exchanges(user_id: int) -> int:
        """Посчитать успешные обмены пользователя"""
        result = db.execute_query(
            """SELECT COUNT(*) AS count FROM exchanges 
               WHERE (offer1_user_id = %s OR offer2_user_id = %s) 
               AND status = 'completed'""",
            (user_id, user_id),
            fetch=True,
        )
        return result[0]["count"] if result else 0


class AuthService:
    @staticmethod
    def generate_token(user_id: int) -> str:
        """Сгенерировать токен для пользователя"""
        return serializer.dumps(user_id)

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """Верифицировать токен и получить ID пользователя"""
        try:
            return serializer.loads(token, max_age=3600 * 24 * 30)
        except Exception:
            return None

    @staticmethod
    def check_user_exists(username: str, email: str) -> bool:
        """Проверить, существует ли пользователь"""
        existing_user = db.execute_query(
            "SELECT id FROM users WHERE username = %s OR email = %s",
            (username, email),
            fetch=True,
        )
        return bool(existing_user)


class FileService:
    @staticmethod
    def save_uploaded_file(file, upload_dir: str, prefix: str, user_id: Optional[int] = None) -> Optional[str]:
        """Сохранить загруженный файл"""
        if not file or not file.filename:
            return None
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(file.filename)[1]
        
        if user_id:
            filename = f"{prefix}_{user_id}_{ts}{ext}"
        else:
            filename = f"{prefix}_{ts}{ext}"
        
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return filename

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Удалить файл"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            print(f"Ошибка при удалении файла: {e}")
        return False


class MessageService:
    @staticmethod
    def send_message(
        sender_id: int,
        recipient_id: int,
        message: str,
        offer_id: Optional[int] = None
    ) -> bool:
        """Отправить сообщение"""
        # Проверяем существование получателя
        recipient = db.execute_query(
            "SELECT id FROM users WHERE id = %s", (recipient_id,), fetch=True
        )
        
        if not recipient:
            return False
        
        # Проверяем существование объявления, если указано
        if offer_id:
            offer = db.execute_query(
                "SELECT id FROM offers WHERE id = %s AND is_active = TRUE", 
                (offer_id,), 
                fetch=True
            )
            if not offer:
                offer_id = None
        
        try:
            db.execute_query(
                """INSERT INTO messages (sender_id, recipient_id, offer_id, message)
                   VALUES (%s, %s, %s, %s)""",
                (sender_id, recipient_id, offer_id, message.strip()),
            )
            return True
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return False
    
    @staticmethod
    def get_conversation(
        user1_id: int,
        user2_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получить переписку между двумя пользователями - ИСПРАВЛЕНО: ASC вместо DESC"""
        query = """
            SELECT 
                m.*,
                s.username as sender_username,
                s.avatar_url as sender_avatar,
                r.username as recipient_username,
                r.avatar_url as recipient_avatar,
                o.give as offer_title
            FROM messages m
            JOIN users s ON m.sender_id = s.id
            JOIN users r ON m.recipient_id = r.id
            LEFT JOIN offers o ON m.offer_id = o.id
            WHERE (m.sender_id = %s AND m.recipient_id = %s)
               OR (m.sender_id = %s AND m.recipient_id = %s)
            ORDER BY m.created_at ASC  # ВАЖНО: ASC вместо DESC!
            LIMIT %s OFFSET %s
        """
        
        messages = db.execute_query(
            query, 
            (user1_id, user2_id, user2_id, user1_id, limit, offset), 
            fetch=True
        ) or []
        
        # Помечаем сообщения как прочитанные
        if messages:
            db.execute_query(
                """UPDATE messages 
                   SET is_read = TRUE 
                   WHERE recipient_id = %s AND sender_id = %s AND is_read = FALSE""",
                (user1_id, user2_id),
            )
        
        return messages  # Теперь сообщения идут от старых к новым
    
    @staticmethod
    def get_user_dialogs(user_id: int) -> List[Dict[str, Any]]:
        """Получить список диалогов пользователя с последними сообщениями"""
        query = """
            SELECT 
                other_user.id as other_user_id,
                other_user.username as other_username,
                other_user.avatar_url as other_avatar,
                last_message.message as last_message_text,
                last_message.created_at as last_message_time,
                last_message.sender_id = %s as is_my_message,
                unread_count.count as unread_count
            FROM (
                SELECT DISTINCT 
                    CASE 
                        WHEN sender_id = %s THEN recipient_id
                        ELSE sender_id
                    END as other_user_id
                FROM messages
                WHERE sender_id = %s OR recipient_id = %s
            ) as dialog_partners
            JOIN users other_user ON dialog_partners.other_user_id = other_user.id
            LEFT JOIN (
                SELECT 
                    sender_id,
                    recipient_id,
                    message,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY LEAST(sender_id, recipient_id), GREATEST(sender_id, recipient_id) 
                                      ORDER BY created_at DESC) as rn
                FROM messages
                WHERE sender_id = %s OR recipient_id = %s
            ) last_message ON (
                (last_message.sender_id = %s AND last_message.recipient_id = other_user.id) OR
                (last_message.sender_id = other_user.id AND last_message.recipient_id = %s)
            ) AND last_message.rn = 1
            LEFT JOIN (
                SELECT 
                    sender_id,
                    COUNT(*) as count
                FROM messages
                WHERE recipient_id = %s AND is_read = FALSE
                GROUP BY sender_id
            ) unread_count ON unread_count.sender_id = other_user.id
            ORDER BY last_message.created_at DESC
        """
        
        return db.execute_query(
            query, 
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id), 
            fetch=True
        ) or []
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Получить количество непрочитанных сообщений"""
        result = db.execute_query(
            "SELECT COUNT(*) as count FROM messages WHERE recipient_id = %s AND is_read = FALSE",
            (user_id,),
            fetch=True,
        )
        return result[0]["count"] if result else 0
    
    @staticmethod
    def mark_as_read(message_ids: List[int], user_id: int) -> bool:
        """Пометить сообщения как прочитанные"""
        if not message_ids:
            return True
        
        placeholders = ','.join(['%s'] * len(message_ids))
        query = f"""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE id IN ({placeholders}) AND recipient_id = %s
        """
        
        params = message_ids + [user_id]
        db.execute_query(query, params)
        return True
    
    @staticmethod
    def delete_message(message_id: int, user_id: int) -> bool:
        """Удалить сообщение (только для отправителя)"""
        # Проверяем, принадлежит ли сообщение пользователю
        message = db.execute_query(
            "SELECT id FROM messages WHERE id = %s AND sender_id = %s",
            (message_id, user_id),
            fetch=True,
        )
        
        if not message:
            return False
        
        db.execute_query(
            "DELETE FROM messages WHERE id = %s",
            (message_id,),
        )
        return True