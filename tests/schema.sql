-- Database schema for FastAPI Blog application

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL,
    username VARCHAR(25) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    author VARCHAR(25) NOT NULL,
    image VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author) REFERENCES users(username) ON DELETE CASCADE
);

-- Add some test data (optional)
INSERT IGNORE INTO users (name, email, username, password) VALUES 
('Test User', 'test@example.com', 'testuser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewCyNJzJkp3n2XbO');

INSERT IGNORE INTO articles (title, body, author) VALUES 
('Welcome to FastAPI Blog', 'This is a test article created during database initialization. FastAPI Blog is a modern, high-performance blog application built with FastAPI framework.', 'testuser'),
('Getting Started', 'Learn how to use this blog application. You can create, edit, and delete articles through the user-friendly interface.', 'testuser');
