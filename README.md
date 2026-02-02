
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

5. Start the ASGI server:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

. Open `http://localhost:8000` in your browser.

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
{"type": "chat_message", "message_id": 1, "message": "Hello!", "sender_id": 2, "sender_username": "Qasim1", "timestamp": "...", "is_delivered": true, "is_read": false}

// Typing indicator
{"type": "typing", "user_id": 2, "username": "Qasim1", "is_typing": true}

// Online/offline status
{"type": "user_status", "user_id": 2, "username": "Qasim1", "status": "online"}

// Read receipt
{"type": "read_receipt", "message_ids": [1, 2], "reader_id": 2}
```


---

