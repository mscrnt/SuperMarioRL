# Base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
 && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application directory
COPY app/ ./app

# Expose the Flask app port
EXPOSE 5000

# Set the entry point for Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
