# Real-Time Chat Application

A Django-based real-time chat application using Django Channels (WebSockets), JWT authentication, and MySQL.

## Features

### Must-Have
- **JWT Authentication** – Register / login via REST endpoints; tokens used for both API and WebSocket auth
- **Real-time messaging** – Django Channels WebSocket consumer with instant message delivery
- **Message persistence** – Every message stored in MySQL before broadcast
- **Access control** – Only authenticated chat participants can connect, send, or receive messages
- **Chat history API** – `GET /api/chat/history/<user_id>/` returns messages ordered oldest → newest

### Bonus (all implemented)
- **Typing indicator** – Live "user is typing…" events over WebSocket
- **Online / offline status** – Tracked via `UserProfile` and broadcast on connect/disconnect
- **Message delivery & read status** – `is_delivered` set when the receiver's socket receives the message; `is_read` set via explicit read-receipt events
- **Docker setup** – `docker-compose.yml` with MySQL, Redis, and the Django app
- **Unit tests** – Accounts and chat test suites covering models, API endpoints, and persistence logic

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 4.2, Django REST Framework |
| WebSockets | Django Channels 4 + Daphne |
| Auth | djangorestframework-simplejwt (JWT) |
| Channel Layer | Redis 7 via channels-redis |
| Database | MySQL 8 |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
Django_message_app/
├── config/             # Django project settings, URLs, ASGI/WSGI
├── accounts/           # User registration, JWT login, user profiles
├── chat/               # Message model, history API, WebSocket consumer
│   ├── consumers.py    # Async WebSocket consumer
│   ├── middleware.py   # JWT auth middleware for Channels
│   └── routing.py      # WebSocket URL routing
├── templates/chat/     # Minimal functional chat UI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

---

## Setup

### Prerequisites

- Python 3.11+
- MySQL server running (or use Docker)
- Redis server running (or use Docker)

### Option A – Docker (recommended)

1. Create a `.env` file in the project root:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=django
DB_USER=root
DB_PASSWORD=your_password
```

2. Build and start all services:

```bash
docker-compose up --build
```

The app will be available at `http://localhost:8000`.

### Option B – Local development

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure the `.env` file with your MySQL and Redis credentials.

4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser (optional, for admin panel):

```bash
python manage.py createsuperuser
```

6. Start the ASGI server:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

7. Open `http://localhost:8000` in your browser.

---

## API Endpoints

### Authentication

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/auth/register/` | None | Register a new user |
| POST | `/api/auth/login/` | None | Obtain JWT access + refresh tokens |
| POST | `/api/auth/token/refresh/` | None | Refresh an expired access token |
| GET | `/api/auth/users/` | Bearer | List all users (with online status) |
| GET | `/api/auth/users/<id>/` | Bearer | Get single user details |

### Chat

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/chat/history/<user_id>/` | Bearer | Message history with a user (oldest → newest) |

### WebSocket

```
ws://localhost:8000/ws/chat/<user_id>/?token=<jwt_access_token>
```

**Sending messages (JSON payloads):**

```json
// Send a chat message
{"type": "chat_message", "message": "Hello!"}

// Typing indicator
{"type": "typing", "is_typing": true}

// Mark messages as read
{"type": "read_receipt", "message_ids": [1, 2, 3]}
```

**Receiving events:**

```json
// Incoming message
{"type": "chat_message", "message_id": 1, "message": "Hello!", "sender_id": 2, "sender_username": "bob", "timestamp": "...", "is_delivered": true, "is_read": false}

// Typing indicator
{"type": "typing", "user_id": 2, "username": "bob", "is_typing": true}

// Online/offline status
{"type": "user_status", "user_id": 2, "username": "bob", "status": "online"}

// Read receipt
{"type": "read_receipt", "message_ids": [1, 2], "reader_id": 2}
```

---

## Running Tests

```bash
python manage.py test accounts chat --verbosity=2
```

> **Note:** Tests use Django's default test database. For the unit tests provided, no Redis connection is required (they test the ORM and REST layers only).

---

## Security

- **No hard-coded credentials** – All DB/secret values loaded from environment variables
- **JWT-only WebSocket auth** – Token validated in custom Channels middleware before the consumer runs
- **Participant-only access** – Consumer rejects connections from users not involved in the chat
- **CSRF protection** – Active on all Django views via middleware
- **Message isolation** – History API filters by `(sender, receiver)` pair; users cannot read other conversations
