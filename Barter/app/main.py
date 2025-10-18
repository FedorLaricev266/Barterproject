from fastapi import FastAPI
from pydantic import BaseModel
what_you_have = ("")
what_you_want = ("")
app = FastAPI()

@app.get("/")
def home():
    return {"Добро пожаловать на наш сайт!Здесь вы можете обменять ненужные вещи на что то другое"}

from fastapi import FastAPI
@app.get("/about")
def about():
    return {"about": "Этот сайт создан в рамках проекта 'Сайт для бартерного обменя'", "version": "1.0"}

@app.get("/addoffer")
def addoffer():
    return{"Что вы хотите поменять: ПОКА НЕ ЗНАЮ КАК СДЕЛАТЬ ВВОД"
"Что вы хотите получить: ПОКА НЕ ЗНАЮ КАК СДЕЛАТЬ ВВОД"}

@app.get("/offer")
def offer():
    return{"Отдаёте:"
           " Получаете:"}

import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000)
