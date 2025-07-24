# FastAPI Blog - Modern Blog Application

A high-performance, modern blog application built with FastAPI, featuring async operations, JWT authentication, and comprehensive API documentation.

## 🚀 Features

- **Modern FastAPI Framework**: High-performance, modern Python web framework
- **Async/Await Support**: Asynchronous database operations for better performance
- **JWT Authentication**: Secure token-based authentication with cookie support
- **Pydantic Validation**: Automatic request/response validation and serialization
- **Interactive API Documentation**: Auto-generated API docs with Swagger UI
- **Type Hints**: Full type safety throughout the application
- **Security Improvements**: Protected against SQL injection with parameterized queries
- **Modular Architecture**: Clean separation of concerns with routers and dependencies

## 📋 Core Functionalities

- ✅ User authentication and registration
- ✅ Create, read, update, and delete articles
- ✅ User dashboard for managing articles
- ✅ Public article listing and viewing
- ✅ Responsive web interface
- ✅ MySQL database integration

## 🏗️ Architecture

```
src/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Application configuration
│   ├── security.py        # Authentication and security utilities
│   └── schemas.py         # Pydantic models for validation
├── database/
│   └── connection.py      # Database connection and table management
├── routers/
│   ├── auth.py           # Authentication routes
│   ├── articles.py       # Article management routes
│   ├── dashboard.py      # Dashboard routes
│   └── pages.py          # Static page routes
├── templates/            # Jinja2 HTML templates
├── static/              # CSS, JS, and image files
└── init_app.py          # Database initialization script
```

## 🛠️ Prerequisites

- Python 3.8+
- MySQL 5.7+ or 8.0+
- Docker (optional, for MySQL setup)

## 🚀 Quick Start

### 1. Database Setup

**Option A: Using Docker (Recommended)**
```bash
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=secret_pass mysql:8.0
```

**Option B: Local MySQL Installation**
Install MySQL locally and create a database named `blog_db`.

### 2. Clone and Setup

```bash
# Run the comprehensive setup script
./scripts/setup.sh
```

Or manually:

```bash
# Install dependencies
./scripts/install_dependencies.sh

# Setup environment
cp .env.example src/.env
# Edit src/.env with your database credentials

# Initialize database
cd src && python init_app.py
```

### 3. Start the Application

```bash
cd src
uvicorn main:app --reload
```

## 🌐 Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## � Docker Deployment

```bash
# Using docker-compose
docker-compose up -d

# The application will be available at http://localhost:8000
# phpMyAdmin at http://localhost:8080
```

## 📚 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `GET /auth/login` - Login page
- `GET /auth/register` - Registration page

### Articles
- `GET /api/articles/` - List all articles
- `POST /api/articles/` - Create new article (auth required)
- `GET /api/articles/{id}` - Get single article
- `PUT /api/articles/{id}` - Update article (auth required)
- `DELETE /api/articles/{id}` - Delete article (auth required)

### Dashboard
- `GET /dashboard/` - User dashboard (auth required)
- `GET /dashboard/add_article` - Add article page (auth required)
- `GET /dashboard/edit_article/{id}` - Edit article page (auth required)

### Pages
- `GET /` - Home page
- `GET /about` - About page

## 🧪 Testing

```bash
# Run tests
./scripts/run_tests.sh

# Run tests with verbose output
./scripts/run_tests.sh -v

# Run tests on custom port
./scripts/run_tests.sh --port 8080
```

## ⚙️ Configuration

Environment variables can be set in `src/.env`:

```env
# Database configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret_pass
DB_NAME=blog_db

# Security
SECRET_KEY=your-secret-key-here-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application settings
DEBUG=True
APP_NAME="FastAPI Blog"
APP_VERSION="1.0.0"
```

## 📦 Dependencies

Key dependencies:
- `fastapi` - Modern web framework
- `uvicorn` - ASGI server
- `aiomysql` - Async MySQL driver
- `python-jose` - JWT handling
- `passlib` - Password hashing
- `pydantic` - Data validation
- `jinja2` - Template engine

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Performance**: FastAPI provides 2-3x better performance compared to traditional Flask applications through async operations and modern Python features.
