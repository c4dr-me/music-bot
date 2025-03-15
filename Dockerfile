FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    libopus-dev \
    opus-tools \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Copy the rest of the application code
COPY . .

# Make setup.sh executable and run it
RUN chmod +x setup.sh && ./setup.sh

# Set the entry point to run the application
CMD ["python", "main.py"]
