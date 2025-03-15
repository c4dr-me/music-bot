FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Install dependencies globally (not in venv)
RUN pip install --no-cache-dir -r requirements.txt --timeout=60 -i https://pypi.org/simple

COPY . .

CMD ["python", "main.py"]
