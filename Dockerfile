
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install opus-tools
RUN apt-get update && apt-get install -y opus-tools

# Copy the rest of the application code
COPY . .

# Make setup.sh executable
RUN chmod +x setup.sh

# Run the setup script
RUN ./setup.sh

# Set the entry point to run the application
CMD ["python", "main.py"]