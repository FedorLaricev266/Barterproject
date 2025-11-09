from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

#Создание подключения к базе данных SQLite
DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    registration_date = Column(DateTime, default=datetime.datetime.utcnow)
    rating = Column(Integer, default=0)

    offers = relationship("Offer", back_populates="owner")


#МОДЕЛЬ ОБЪЯВЛЕНИЯ
class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    give = Column(String, nullable=False)
    get = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="offers")


#ФУНКЦИЯ СОЗДАНИЯ БД
def init_db():
    Base.metadata.create_all(bind=engine)
