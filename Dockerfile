# ローカル開発・テスト用のイメージです。本番デプロイには使っていません。
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --root-user-action=ignore --require-hashes -r requirements.txt -r requirements-dev.txt

RUN useradd --create-home app && chown app:app /app
COPY --chown=app:app . .
USER app

EXPOSE 8000
# SQLite はコンテナ内に作るので、コンテナを消すとデータも消えます。
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
