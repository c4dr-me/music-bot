FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y libopus0 ffmpeg

# Create working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the bot files
COPY . .

# Start the bot
CMD ["python", "main.py"]
