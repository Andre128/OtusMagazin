from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
import psycopg2
import pandas as pd
from contextlib import contextmanager
import uvicorn
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY
from starlette.middleware.base import BaseHTTPMiddleware
import time

app = FastAPI()

# Конфигурация базы данных
DB_NAME = os.getenv('DB_NAME', 'mydb')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')

CSV_FILE = "test_data.csv"

# Контекстные менеджеры для работы с БД
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            cursor.close()

# Создание таблицы
def create_table_if_not_exists():
    with get_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                clientID SERIAL PRIMARY KEY,
                firstName VARCHAR(100),
                lastName VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                login VARCHAR(50)
            );
        """)

# Загрузка данных из CSV
def load_data_from_csv():
    with get_db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM clients;")
        count = cursor.fetchone()[0]

        if count == 0:
            try:
                df = pd.read_csv(CSV_FILE)
                for _, row in df.iterrows():
                    cursor.execute(
                        "INSERT INTO clients (firstName, lastName, email, phone, login) VALUES (%s, %s, %s, %s, %s)",
                        (row['firstName'], row['lastName'], row['email'], row['phone'], row['login'])
                    )
                print("Тестовые данные загружены.")
            except Exception as e:
                print(f"Ошибка загрузки данных из CSV: {e}")

# Метрики Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total", "Total count of HTTP requests", ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Latency of HTTP requests", ["method", "endpoint"]
)

# Middleware для сбора метрик
class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

        return response

app.add_middleware(PrometheusMiddleware)

# Модель пользователя
class Clients(BaseModel):
    firstName: str
    lastName: str
    email: str
    phone: str
    login: str

class UserOut(Clients):
    id: int

# Эндпоинт для сбора метрик Prometheus
@app.get("/metrics")
def metrics():
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST

# API эндпоинты
@app.post("/users/", response_model=UserOut)
def create_client(client: Clients):
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO clients (firstName, lastName, email, phone, login) VALUES (%s, %s, %s, %s, %s) RETURNING clientID",
                (client.firstName, client.lastName, client.email, client.phone, client.login)
            )
            clientid = cursor.fetchone()[0]
            return {"id": clientid, **client.dict()}
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

@app.get("/users/", response_model=List[UserOut])
def get_users():
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT clientID, firstName, lastName, email, phone, login FROM clients")
            users = cursor.fetchall()
            return [{"id": u[0], "firstName": u[1], "lastName": u[2], "email": u[3], "phone": u[4], "login": u[5]} for u in users]
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT clientID, firstName, lastName, email, phone, login FROM clients WHERE clientID = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            return {"id": user[0], "firstName": user[1], "lastName": user[2], "email": user[3], "phone": user[4], "login": user[5]}
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, client: Clients):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE clients 
                SET firstName = %s, lastName = %s, email = %s, phone = %s, login = %s 
                WHERE clientID = %s
                """,
                (client.firstName, client.lastName, client.email, client.phone, client.login, user_id)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            return {"id": user_id, **client.dict()}
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM clients WHERE clientID = %s", (user_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            return {"message": "Пользователь успешно удалён"}
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

# Запуск приложения
if __name__ == "__main__":
    create_table_if_not_exists()
    load_data_from_csv()
    uvicorn.run("restfulcrud:app", host="0.0.0.0", port=80, reload=True)
