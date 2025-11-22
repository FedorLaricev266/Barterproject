import mysql.connector
from mysql.connector import Error
import os

class Database:
    def __init__(self):
        self.host = 'localhost'
        self.database = 'exchange_db'
        self.user = 'exchange_user'
        self.password = 'exchange_password'
        self.port = 3306
    
    def get_connection(self):
        try:
            print(f"Подключаюсь к MySQL...")
            print(f"Хост: {self.host}:{self.port}")
            print(f"База: {self.database}")
            print(f"Пользователь: {self.user}")
            
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                auth_plugin='mysql_native_password'
            )
            print("Успешное подключение к БД!")
            return connection
        except Error as e:
            print(f"Ошибка подключения: {e}")
            print("Возможные проблемы:")
            print("1. Неправильный пароль")
            print("2. Пользователь не существует")
            print("3. База данных не существует")
            print("4. MySQL сервер не запущен")
            return None
    
    def execute_query(self, query, params=None, fetch=False):
        connection = self.get_connection()
        if connection is None:
            print("Не могу выполнить запрос - нет подключения")
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                print(f"Запрос выполнен, строк: {len(result)}")
            else:
                connection.commit()
                result = cursor.lastrowid
                print(f"Запрос выполнен, ID: {result}")
            
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