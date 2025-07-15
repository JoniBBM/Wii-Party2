-- Database initialization script for Wii Party U Deluxe
-- This script runs when the PostgreSQL container starts for the first time

-- Create database (already created by POSTGRES_DB env var)
-- CREATE DATABASE wii_party;

-- Create user (already created by POSTGRES_USER env var)
-- CREATE USER wii_party_user WITH PASSWORD 'secure_db_password_2024';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE wii_party TO wii_party_user;

-- Connect to the database
\c wii_party;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO wii_party_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wii_party_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wii_party_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO wii_party_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO wii_party_user;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual table creation will be handled by Flask-Migrate
-- This script just ensures the database and user are properly set up