FROM astral/uv:python3.14-alpine AS base

USER root

WORKDIR /app

COPY . .

RUN apk add git

RUN uv sync

CMD ["uv", "run", "main.py"]
