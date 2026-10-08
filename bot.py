import logging
import os
import re

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

DOWNTIFY_URL = os.getenv(
    "DOWNTIFY_URL",
    "http://192.168.0.123:9000"
).rstrip("/")

DOWNTIFY_TOKEN = os.getenv("DOWNTIFY_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

ALLOWED_USER_ID = int(
    os.getenv("TELEGRAM_ALLOWED_USER_ID", "0")
)

ALLOWED_CHAT_ID = int(
    os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "0")
)

ALLOWED_THREAD_ID = int(
    os.getenv("TELEGRAM_ALLOWED_THREAD_ID", "0")
)

# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# CLIENTE HTTP
# ============================================================

client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0, connect=10.0)
)

# ============================================================
# AUTORIZAÇÃO
# ============================================================


def is_authorized(update: Update) -> bool:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = user.id if user else None
    chat_id = chat.id if chat else None
    thread_id = message.message_thread_id if message else None

    authorized = (
        user_id == ALLOWED_USER_ID
        and chat_id == ALLOWED_CHAT_ID
        and thread_id == ALLOWED_THREAD_ID
    )

    if not authorized:
        logger.warning(
            "Mensagem bloqueada | user=%s | chat=%s | thread=%s",
            user_id,
            chat_id,
            thread_id,
        )

    return authorized


# ============================================================
# DOWNTIFY API
# ============================================================


def auth_headers():
    if not DOWNTIFY_TOKEN:
        return {}

    return {
        "Authorization": f"Bearer {DOWNTIFY_TOKEN}",
    }


async def downtify_get(path, **kwargs):
    return await client.get(
        f"{DOWNTIFY_URL}{path}",
        headers=auth_headers(),
        **kwargs,
    )


async def downtify_post(path, **kwargs):
    return await client.post(
        f"{DOWNTIFY_URL}{path}",
        headers=auth_headers(),
        **kwargs,
    )


# ============================================================
# EXTRAÇÃO DE URL
# ============================================================

URL_RE = re.compile(
    r"https?://[^\s<>]+",
    re.IGNORECASE,
)


def extract_url(text: str):
    match = URL_RE.search(text or "")

    if not match:
        return None

    return match.group(0).rstrip(".,!?)]}")


# ============================================================
# /start
# ============================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    await update.message.reply_text(
        "🎵 *Downtify Telegram*\n\n"
        "Olá! 👋\n\n"
        "Envie uma URL do Spotify, YouTube ou outra URL "
        "compatível com o Downtify para iniciar um download.\n\n"
        "Use /help para ver todos os comandos disponíveis.",
        parse_mode="Markdown",
    )


# ============================================================
# /help
# ============================================================


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    help_text = (
        "🎵 *Downtify Telegram — Ajuda*\n\n"

        "📥 *DOWNLOAD*\n"
        "Envie diretamente uma URL do Spotify, YouTube ou outra "
        "fonte compatível com o Downtify.\n\n"
        "Exemplo:\n"
        "`https://open.spotify.com/track/...`\n\n"

        "🤖 *COMANDOS*\n\n"

        "*/start*\n"
        "Inicia o bot e mostra uma breve explicação.\n\n"

        "*/help*\n"
        "Mostra esta tela de ajuda.\n\n"

        "*/status*\n"
        "Verifica se o Downtify está online e respondendo.\n\n"

        "*/queue*\n"
        "Mostra o conteúdo atual da fila de downloads do Downtify.\n\n"

        "📌 *COMO USAR*\n\n"
        "1. Envie uma URL neste tópico.\n"
        "2. O bot consulta o Downtify.\n"
        "3. A URL é adicionada à fila de download.\n"
        "4. O Downtify realiza o download.\n\n"

        "🔒 *Acesso*\n"
        "Este bot está restrito a este tópico do Telegram."
    )

    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
    )


# ============================================================
# /status
# ============================================================


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    try:
        response = await downtify_get("/api/health")

        if response.status_code == 200:
            try:
                data = response.json()
                details = str(data)
            except Exception:
                details = response.text

            await update.message.reply_text(
                "🟢 *Downtify online*\n\n"
                f"{details}",
                parse_mode="Markdown",
            )

        else:
            await update.message.reply_text(
                "🔴 *Downtify com problema*\n\n"
                f"HTTP {response.status_code}\n"
                f"{response.text[:1000]}",
                parse_mode="Markdown",
            )

    except Exception as exc:
        logger.exception("Erro ao consultar status")

        await update.message.reply_text(
            "🔴 *Erro ao consultar o Downtify*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# /queue
# ============================================================


async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    try:
        response = await downtify_get("/api/queue")

        if response.status_code != 200:
            await update.message.reply_text(
                "❌ Erro ao consultar a fila.\n\n"
                f"HTTP {response.status_code}\n"
                f"{response.text[:1000]}"
            )
            return

        data = response.json()

        # Formatação simples e segura para Telegram
        formatted = str(data)

        if len(formatted) > 3500:
            formatted = formatted[:3500] + "\n..."

        await update.message.reply_text(
            "📋 *Fila do Downtify*\n\n"
            f"`{formatted}`",
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception("Erro ao consultar fila")

        await update.message.reply_text(
            "🔴 *Erro ao consultar a fila*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# DOWNLOAD
# ============================================================


async def process_url(update: Update, url: str):
    message = update.message

    await message.reply_text(
        "🔎 Consultando o Downtify..."
    )

    try:
        # ----------------------------------------------------
        # Resolve URL
        # ----------------------------------------------------

        response = await downtify_get(
            "/api/url/resolve",
            params={"url": url},
        )

        if response.status_code != 200:
            await message.reply_text(
                "❌ Não foi possível resolver a URL.\n\n"
                f"HTTP {response.status_code}\n"
                f"{response.text[:1000]}"
            )
            return

        resolved = response.json()

        logger.info(
            "URL resolvida: %s",
            resolved,
        )

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        await message.reply_text(
            "⬇️ Enviando para o Downtify..."
        )

        response = await downtify_post(
            "/api/download/url",
            params={"url": url},
            json=resolved,
        )

        if response.status_code not in (
            200,
            201,
            202,
        ):
            await message.reply_text(
                "❌ O Downtify recusou o download.\n\n"
                f"HTTP {response.status_code}\n"
                f"{response.text[:1500]}"
            )
            return

        try:
            result = response.json()
        except Exception:
            result = response.text

        logger.info(
            "Download enviado: %s",
            result,
        )

        await message.reply_text(
            "✅ *Download enviado para o Downtify!*\n\n"
            f"{result}",
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception(
            "Erro durante download"
        )

        await message.reply_text(
            "❌ *Erro ao comunicar com o Downtify:*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# MENSAGENS
# ============================================================


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_authorized(update):
        return

    text = update.effective_message.text or ""

    url = extract_url(text)

    if not url:
        await update.effective_message.reply_text(
            "❓ Não encontrei nenhuma URL nessa mensagem.\n\n"
            "Use /help para ver como utilizar o bot."
        )
        return

    logger.info(
        "URL recebida | user=%s | chat=%s | thread=%s | url=%s",
        update.effective_user.id,
        update.effective_chat.id,
        update.effective_message.message_thread_id,
        url,
    )

    await process_url(
        update,
        url,
    )


# ============================================================
# MAIN
# ============================================================


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não configurado."
        )

    if not DOWNTIFY_TOKEN:
        raise RuntimeError(
            "DOWNTIFY_TOKEN não configurado."
        )

    logger.info(
        "Downtify Telegram bot iniciado."
    )

    logger.info(
        "Downtify: %s",
        DOWNTIFY_URL,
    )

    logger.info(
        "Telegram autorizado: %s",
        ALLOWED_USER_ID,
    )

    logger.info(
        "Chat autorizado: %s",
        ALLOWED_CHAT_ID,
    )

    logger.info(
        "Thread autorizado: %s",
        ALLOWED_THREAD_ID,
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("status", status)
    )

    application.add_handler(
        CommandHandler("queue", queue)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler,
        )
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
