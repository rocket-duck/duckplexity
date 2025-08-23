FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . /app

CMD ["python", "-m", "bot.main"]
