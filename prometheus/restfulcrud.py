from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time

app = FastAPI()

# Метрики Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Latency of HTTP requests", ["method", "endpoint"]
)


@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    """Middleware для сбора метрик запросов."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(process_time)

    return response


@app.get("/metrics")
def metrics():
    """Эндпоинт для экспорта метрик Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
