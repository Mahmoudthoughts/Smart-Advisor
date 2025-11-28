-- Migration: add role column to users table for role-based access control
ALTER TABLE IF EXISTS users
ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';

-- Ensure existing rows receive the default role
UPDATE users SET role = 'user' WHERE role IS NULL;
