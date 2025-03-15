FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    libpq-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt --timeout=60 -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD ["python", "main.py"]
