
from database import db

def test_connection():
    print("🧪 ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    print("=" * 50)
    
    # Тест 1: Простой запрос
    print("1. Тестируем базовое подключение...")
    result = db.execute_query("SELECT 1 as connection_test", fetch=True)
    if result:
        print("   ✅ Базовое подключение работает!")
    else:
        print("   ❌ Базовое подключение не работает!")
        return False
    
    # Тест 2: Проверяем базу данных
    print("\n2. Проверяем базу данных...")
    result = db.execute_query("SHOW TABLES", fetch=True)
    if result:
        print(f"   ✅ Таблицы в базе: {len(result)}")
        for table in result:
            print(f"      - {list(table.values())[0]}")
    else:
        print("   ❌ Не могу получить список таблиц")
        return False
    
    # Тест 3: Проверяем пользователей
    print("\n3. Проверяем пользователей...")
    users = db.execute_query("SELECT * FROM users", fetch=True)
    if users:
        print(f"   ✅ Найдено пользователей: {len(users)}")
        for user in users:
            print(f"      - {user['username']} (ID: {user['id']})")
    else:
        print("   ❌ Пользователи не найдены")
        return False
    
    # Тест 4: Проверяем объявления
    print("\n4. Проверяем объявления...")
    offers = db.execute_query("SELECT * FROM offers", fetch=True)
    if offers:
        print(f"   ✅ Найдено объявлений: {len(offers)}")
    else:
        print("   ❌ Объявления не найдены")
    
    print("\n" + "=" * 50)
    print("🎉 ТЕСТ ЗАВЕРШЕН!")
    return True

if __name__ == "__main__":
    test_connection()