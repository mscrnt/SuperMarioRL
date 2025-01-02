# Base image
FROM python:3.10-slim

# Install system dependencies including PostgreSQL server
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    postgresql \
    postgresql-contrib \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Set environment variables for PostgreSQL
ENV POSTGRES_USER=mario
ENV POSTGRES_PASSWORD=peach
ENV POSTGRES_DB=mariodb

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application directory
COPY app/ ./app

# Copy PostgreSQL initialization script
COPY init_postgres.sh /docker-entrypoint-initdb.d/init_postgres.sh
RUN chmod +x /docker-entrypoint-initdb.d/init_postgres.sh

# Expose the Flask and PostgreSQL ports
EXPOSE 5000 5432 6006

# Set the entry point to the initialization script
CMD ["/docker-entrypoint-initdb.d/init_postgres.sh"]
