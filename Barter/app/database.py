import os
from urllib.parse import urlparse
import mysql.connector
from mysql.connector import Error


class Database:
    def __init__(self):
        self.host = os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost"))
        self.database = os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "exchange_db"))
        self.user = os.getenv("MYSQLUSER", os.getenv("DB_USER", "exchange_user"))
        self.password = os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "exchange_password"))
        self.port = int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306")))

        # Поддержка DATABASE_URL / MYSQL_URL (mysql://user:pass@host:port/db)
        db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
        if db_url:
            self._load_from_url(db_url)

    def _load_from_url(self, db_url: str):
        parsed = urlparse(db_url)
        if parsed.scheme.startswith("mysql"):
            self.host = parsed.hostname or self.host
            self.port = parsed.port or self.port
            self.user = parsed.username or self.user
            self.password = parsed.password or self.password
            self.database = (parsed.path or "/").lstrip("/") or self.database

    def get_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                auth_plugin='mysql_native_password'
            )
            return connection
        except Error as e:
            print(f"Ошибка подключения к БД: {e}")
            return None

    def execute_query(self, query, params=None, fetch=False):
        connection = self.get_connection()
        if connection is None:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.lastrowid

            cursor.close()
            return result
        except Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            print(f"Запрос: {query}")
            return None
        finally:
            if connection.is_connected():
                connection.close()


db = Database()
