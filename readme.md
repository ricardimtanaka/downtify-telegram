# Downtify Telegram Bot

Telegram bot for interacting with a self-hosted [Downtify](https://github.com/henriquesebastiao/downtify) instance.

The bot allows authorized Telegram users to start music downloads through the Downtify API.

## Features

* `/start` — start the bot
* `/help` — display available commands
* `/status` — check Downtify availability
* `/queue` — check the Downtify queue
* `/download URL` — download a single track
* `/playlist URL` — download a playlist
* Direct URL support
* Telegram user authorization
* Chat authorization
* Topic/thread authorization
* Downtify device-token authentication
* Docker Compose deployment

---

## Architecture

```text
Telegram
   │
   │ Telegram Bot API
   ▼
┌──────────────────────┐
│  Downtify Telegram   │
│        Bot           │
└──────────┬───────────┘
           │
           │ HTTP API
           ▼
┌──────────────────────┐
│      Downtify        │
│    self-hosted       │
└──────────┬───────────┘
           │
           ▼
       Downloads
```

---

## Requirements

* Docker
* Docker Compose
* A running Downtify instance
* A Telegram bot
* A valid Downtify device token

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-user>/downtify-telegram.git
cd downtify-telegram
```

Create the environment file:

```bash
cp .env.example .env
```

Edit it:

```bash
nano .env
```

---

## Configuration

Example `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
TELEGRAM_ALLOWED_CHAT_ID=
TELEGRAM_ALLOWED_THREAD_ID=

DOWNTIFY_URL=http://<downtify-host>:<port>
DOWNTIFY_TOKEN=
```

### Environment variables

| Variable                     | Description                  |
| ---------------------------- | ---------------------------- |
| `TELEGRAM_BOT_TOKEN`         | Telegram bot token           |
| `TELEGRAM_ALLOWED_USER_ID`   | Authorized Telegram user ID  |
| `TELEGRAM_ALLOWED_CHAT_ID`   | Authorized chat/group ID     |
| `TELEGRAM_ALLOWED_THREAD_ID` | Authorized topic/thread ID   |
| `DOWNTIFY_URL`               | URL of the Downtify instance |
| `DOWNTIFY_TOKEN`             | Downtify device token        |

All sensitive values should remain in `.env`.

**Never commit `.env` to the repository.**

---

## Telegram authorization

The bot can restrict access using three independent identifiers:

```text
User ID
   │
   ▼
Chat ID
   │
   ▼
Thread / Topic ID
   │
   ▼
Authorized request
```

This allows the bot to be limited to a specific user, chat, and topic.

The values should be configured through environment variables rather than hard-coded in the source code.

---

## Downtify authentication

Downtify exposes both public and authenticated API endpoints.

The health endpoint can be used to check whether Downtify is available:

```text
GET /api/health
```

Protected endpoints require a device token:

```http
Authorization: Bearer dtfy_...
```

For example:

```text
GET /api/url/resolve
POST /api/download/url
POST /api/download/batch
GET /api/queue
```

If the token is invalid or revoked, Downtify may return:

```text
HTTP 401
Invalid or revoked token
```

In that case, generate a new device token using the Downtify pairing mechanism and update `DOWNTIFY_TOKEN`.

---

## Running with Docker Compose

Start the bot:

```bash
docker compose up -d
```

Check the container:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

---

## Commands

### `/start`

Starts the bot and displays basic information.

```text
/start
```

### `/help`

Displays the available commands.

```text
/help
```

### `/status`

Checks the Downtify instance.

```text
/status
```

Example response:

```text
🟢 Downtify online

{'status': 'ok', 'version': '3.x.x'}
```

### `/queue`

Displays the current Downtify queue.

```text
/queue
```

### `/download`

Downloads a track from a supported URL.

```text
/download https://open.spotify.com/track/EXAMPLE
```

### `/playlist`

Downloads a playlist.

```text
/playlist https://open.spotify.com/playlist/EXAMPLE
```

### Direct URLs

A supported URL can also be sent without a command:

```text
https://open.spotify.com/track/EXAMPLE
```

The bot automatically determines whether the URL represents a single track or a playlist.

---

## API flow

### Single track

```text
Telegram
   │
   ▼
/download URL
   │
   ▼
Downtify /api/url/resolve
   │
   ▼
Resolved track
   │
   ▼
Downtify /api/download/url
```

### Playlist

```text
Telegram
   │
   ▼
/playlist URL
   │
   ▼
Downtify /api/url/resolve
   │
   ▼
Track list
   │
   ▼
Downtify /api/download/batch
```

---

## Project structure

```text
downtify-telegram/
├── bot.py
├── Dockerfile
├── compose.yml
├── .env
├── .env.example
├── .gitignore
└── README.md
```

`.env` contains local secrets and must not be committed.

---

## Development

Rebuild the Docker image:

```bash
docker compose build
```

Rebuild and recreate the container:

```bash
docker compose up -d --build --force-recreate
```

Follow the logs:

```bash
docker compose logs -f downtify-telegram
```

---

## Updating

Pull the latest version:

```bash
git pull
```

Rebuild the container:

```bash
docker compose up -d --build
```

---

## Troubleshooting

### `/status` works but `/download` returns HTTP 401

This usually indicates a problem with `DOWNTIFY_TOKEN`.

Verify that the variable exists inside the container without displaying its value:

```bash
docker exec downtify-telegram sh -c \
'test -n "$DOWNTIFY_TOKEN" && echo "DOWNTIFY_TOKEN configured" || echo "DOWNTIFY_TOKEN missing"'
```

You can also compare the SHA-256 hash of the token configured in `.env` with the token inside the container without exposing the token itself:

```bash
echo "Environment file:"
grep '^DOWNTIFY_TOKEN=' .env | cut -d= -f2- | sha256sum

echo "Container:"
docker exec downtify-telegram sh -c \
'printf "%s" "$DOWNTIFY_TOKEN" | sha256sum'
```

The hashes should match.

---

## Security

Do not commit or publish:

```text
.env
TELEGRAM_BOT_TOKEN
DOWNTIFY_TOKEN
```

Do not hard-code credentials in `bot.py`.

Do not publish private infrastructure information such as:

* internal IP addresses;
* private hostnames;
* Telegram IDs;
* personal usernames;
* filesystem paths specific to your server.

If a Telegram bot token is exposed, revoke it immediately and generate a new token.

If a Downtify device token is exposed, revoke it and generate a new one.

---

## License

This project is intended for personal use and integration with a self-hosted Downtify instance.

Check the licenses and terms of use of Downtify and any external services used by it.
