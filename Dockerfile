FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    libopus-dev \
    opus-tools \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .

RUN python -m venv /venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/venv/bin/python", "main.py"]
