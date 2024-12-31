#!/bin/bash

# Ensure the correct ownership and permissions
chown -R postgres:postgres /var/lib/postgresql/15/main
chmod 700 /var/lib/postgresql/15/main

# Start PostgreSQL
service postgresql start

# Wait for PostgreSQL to start
sleep 5

# Configure authentication method to md5
sed -i "s/local   all             all                                     peer/local   all             all                                     md5/" /etc/postgresql/15/main/pg_hba.conf
sed -i "s/host    all             all             127.0.0.1\/32            peer/host    all             all             127.0.0.1\/32            md5/" /etc/postgresql/15/main/pg_hba.conf
sed -i "s/host    all             all             ::1\/128                 peer/host    all             all             ::1\/128                 md5/" /etc/postgresql/15/main/pg_hba.conf

# Reload PostgreSQL to apply changes
service postgresql reload

# Create user and database
su - postgres -c "psql -c \"CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';\""
su - postgres -c "psql -c \"CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;\""

# Start Flask application
cd /app
exec flask run --host=0.0.0.0 --port=5000 
 
