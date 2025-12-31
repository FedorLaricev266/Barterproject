# main.py
from routes import create_app
import uvicorn

# Создание приложения
app = create_app()

# Запуск приложения
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)