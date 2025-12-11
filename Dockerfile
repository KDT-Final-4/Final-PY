FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DISPLAY=:99

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright가 사용하는 Chromium 및 시스템 의존성 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install --with-deps chromium

# Xvfb 구동용 엔트리포인트
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY app ./app

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
