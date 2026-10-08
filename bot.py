import logging
import os
import re
from typing import Any

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
    "http://192.168.0.123:9000",
).rstrip("/")

DOWNTIFY_TOKEN = os.getenv(
    "DOWNTIFY_TOKEN",
    "",
).strip()

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

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
# HTTP
# ============================================================

client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        60.0,
        connect=10.0,
    )
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
# DOWNTIFY HTTP
# ============================================================

def auth_headers() -> dict[str, str]:
    if not DOWNTIFY_TOKEN:
        return {}

    return {
        "Authorization": f"Bearer {DOWNTIFY_TOKEN}",
    }


async def downtify_get(
    path: str,
    **kwargs: Any,
) -> httpx.Response:

    return await client.get(
        f"{DOWNTIFY_URL}{path}",
        headers=auth_headers(),
        **kwargs,
    )


async def downtify_post(
    path: str,
    **kwargs: Any,
) -> httpx.Response:

    return await client.post(
        f"{DOWNTIFY_URL}{path}",
        headers=auth_headers(),
        **kwargs,
    )


# ============================================================
# URL
# ============================================================

URL_RE = re.compile(
    r"https?://[^\s<>]+",
    re.IGNORECASE,
)


def extract_url(text: str) -> str | None:
    match = URL_RE.search(text or "")

    if not match:
        return None

    return match.group(0).rstrip(
        ".,!?)]}"
    )


# ============================================================
# FORMATAÇÃO
# ============================================================

def truncate(
    text: str,
    maximum: int = 3500,
) -> str:

    if len(text) <= maximum:
        return text

    return text[:maximum] + "\n..."


def get_resolved_songs(
    resolved: Any,
) -> list[dict[str, Any]]:

    if isinstance(resolved, list):
        return [
            item
            for item in resolved
            if isinstance(item, dict)
        ]

    if not isinstance(resolved, dict):
        return []

    # Formatos possíveis usados pelo resolver/UI.
    possible_keys = (
        "songs",
        "tracks",
        "items",
    )

    for key in possible_keys:
        value = resolved.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    # Uma URL de música pode resolver diretamente
    # para um único song object.
    if (
        "artist" in resolved
        or "title" in resolved
        or "name" in resolved
    ):
        return [resolved]

    return []


def is_playlist_url(url: str) -> bool:
    url_lower = url.lower()

    return (
        "/playlist" in url_lower
        or "list=" in url_lower
    )


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    await update.message.reply_text(
        "🎵 *Downtify Telegram*\n\n"
        "Olá! 👋\n\n"
        "Envie uma música ou playlist diretamente "
        "neste tópico para iniciar o download.\n\n"
        "Use /help para ver todos os comandos.",
        parse_mode="Markdown",
    )


# ============================================================
# /help
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    text = (
        "🎵 *Downtify Telegram — Ajuda*\n\n"

        "📥 *DOWNLOAD DE MÚSICA*\n\n"
        "`/download URL`\n"
        "Baixa uma música individual.\n\n"
        "Exemplo:\n"
        "`/download https://open.spotify.com/track/...`\n\n"

        "📚 *DOWNLOAD DE PLAYLIST*\n\n"
        "`/playlist URL`\n"
        "Adiciona todas as músicas da playlist à fila.\n\n"
        "Exemplo:\n"
        "`/playlist https://open.spotify.com/playlist/...`\n\n"

        "🔗 *URL DIRETA*\n\n"
        "Você também pode simplesmente enviar a URL "
        "sem comando.\n\n"
        "O bot identifica automaticamente se é uma "
        "música ou playlist.\n\n"

        "🤖 *COMANDOS*\n\n"

        "*/start*\n"
        "Inicia o bot.\n\n"

        "*/help*\n"
        "Mostra esta ajuda.\n\n"

        "*/download URL*\n"
        "Baixa uma música individual.\n\n"

        "*/playlist URL*\n"
        "Baixa uma playlist inteira.\n\n"

        "*/status*\n"
        "Verifica se o Downtify está online.\n\n"

        "*/queue*\n"
        "Mostra a fila de downloads.\n\n"

        "🎧 *FONTES*\n\n"
        "Spotify\n"
        "YouTube\n"
        "YouTube Music\n"
        "Deezer\n\n"

        "🔒 *SEGURANÇA*\n\n"
        "O bot está restrito ao usuário autorizado, "
        "ao chat autorizado e ao tópico configurado."
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# ============================================================
# /status
# ============================================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    try:
        response = await downtify_get(
            "/api/health"
        )

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
                "🔴 *Downtify respondeu com erro*\n\n"
                f"HTTP {response.status_code}\n"
                f"{truncate(response.text, 1500)}",
                parse_mode="Markdown",
            )

    except Exception as exc:

        logger.exception(
            "Erro ao consultar status"
        )

        await update.message.reply_text(
            "🔴 *Erro ao consultar o Downtify*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# /queue
# ============================================================

async def queue(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    try:
        response = await downtify_get(
            "/api/queue"
        )

        if response.status_code != 200:

            await update.message.reply_text(
                "❌ Erro ao consultar a fila.\n\n"
                f"HTTP {response.status_code}\n"
                f"{truncate(response.text, 1500)}"
            )

            return

        data = response.json()

        if not data:
            await update.message.reply_text(
                "📭 A fila do Downtify está vazia."
            )
            return

        lines = [
            "📋 *Fila do Downtify*\n"
        ]

        for index, job in enumerate(
            data,
            start=1,
        ):

            song = job.get(
                "song",
                {}
            )

            if not isinstance(song, dict):
                song = {}

            artist = (
                song.get("artist")
                or job.get("artist")
                or "Artista desconhecido"
            )

            title = (
                song.get("title")
                or song.get("name")
                or job.get("title")
                or "Faixa desconhecida"
            )

            job_status = job.get(
                "status",
                "unknown"
            )

            progress = job.get(
                "progress"
            )

            if isinstance(progress, (int, float)):
                status_text = (
                    f"{job_status} "
                    f"({progress:.0f}%)"
                )
            else:
                status_text = job_status

            lines.append(
                f"{index}. 🎵 {artist} — {title}\n"
                f"   Status: `{status_text}`"
            )

        text = "\n\n".join(lines)

        await update.message.reply_text(
            truncate(text),
            parse_mode="Markdown",
        )

    except Exception as exc:

        logger.exception(
            "Erro ao consultar fila"
        )

        await update.message.reply_text(
            "🔴 *Erro ao consultar a fila*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# RESOLVE URL
# ============================================================

async def resolve_url(
    url: str,
) -> tuple[httpx.Response, Any]:

    response = await downtify_get(
        "/api/url/resolve",
        params={
            "url": url,
        },
    )

    try:
        data = response.json()
    except Exception:
        data = response.text

    return response, data


# ============================================================
# DOWNLOAD DE UMA MÚSICA
# ============================================================

async def download_single(
    update: Update,
    url: str,
):

    message = update.message

    await message.reply_text(
        "🔎 Resolvendo a música..."
    )

    try:

        response, resolved = await resolve_url(
            url
        )

        if response.status_code != 200:

            await message.reply_text(
                "❌ Não foi possível resolver a URL.\n\n"
                f"HTTP {response.status_code}\n"
                f"{truncate(str(resolved), 1500)}"
            )

            return

        songs = get_resolved_songs(
            resolved
        )

        # Se o resolver devolveu uma lista,
        # mas a URL é claramente de playlist,
        # deixamos o fluxo de playlist cuidar dela.
        if len(songs) > 1:

            await download_batch(
                update,
                url,
                songs,
            )

            return

        if not songs:

            # O endpoint /api/download/url aceita
            # o objeto retornado pelo resolver.
            song_body = (
                resolved
                if isinstance(resolved, dict)
                else {}
            )

        else:

            song_body = songs[0]

        title = (
            song_body.get("title")
            or song_body.get("name")
            or "Música"
        )

        artist = song_body.get(
            "artist",
            "Artista desconhecido",
        )

        await message.reply_text(
            "⬇️ *Enviando para o Downtify*\n\n"
            f"🎤 {artist}\n"
            f"🎵 {title}",
            parse_mode="Markdown",
        )

        response = await downtify_post(
            "/api/download/url",
            params={
                "url": url,
            },
            json=song_body,
        )

        if response.status_code not in (
            200,
            201,
            202,
        ):

            await message.reply_text(
                "❌ O Downtify recusou o download.\n\n"
                f"HTTP {response.status_code}\n"
                f"{truncate(response.text, 2000)}"
            )

            return

        try:
            result = response.json()
        except Exception:
            result = response.text

        logger.info(
            "Download individual enviado: %s",
            result,
        )

        await message.reply_text(
            "✅ *Download concluído/enviado!*\n\n"
            f"🎤 {artist}\n"
            f"🎵 {title}\n\n"
            f"Resposta: `{result}`",
            parse_mode="Markdown",
        )

    except Exception as exc:

        logger.exception(
            "Erro no download individual"
        )

        await message.reply_text(
            "❌ *Erro durante o download*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# DOWNLOAD DE PLAYLIST / BATCH
# ============================================================

async def download_batch(
    update: Update,
    url: str,
    songs: list[dict[str, Any]],
):

    message = update.message

    if not songs:

        await message.reply_text(
            "❌ Não encontrei músicas nessa playlist."
        )

        return

    await message.reply_text(
        "📚 *Playlist encontrada*\n\n"
        f"🎵 {len(songs)} músicas\n\n"
        "⬇️ Enviando para a fila do Downtify..."
        ,
        parse_mode="Markdown",
    )

    payload = {
        "songs": songs,
        "playlist_url": url,
        "generate_m3u": True,
    }

    response = await downtify_post(
        "/api/download/batch",
        json=payload,
    )

    if response.status_code not in (
        200,
        201,
        202,
    ):

        await message.reply_text(
            "❌ O Downtify recusou a playlist.\n\n"
            f"HTTP {response.status_code}\n"
            f"{truncate(response.text, 2500)}"
        )

        return

    try:
        result = response.json()
    except Exception:
        result = {
            "response": response.text
        }

    count = result.get(
        "count",
        len(songs),
    )

    job_ids = result.get(
        "job_ids",
        [],
    )

    await message.reply_text(
        "✅ *Playlist adicionada!*\n\n"
        f"🎵 Faixas: *{count}*\n"
        f"📋 Jobs: *{len(job_ids)}*\n"
        "📁 M3U: ativada\n\n"
        "Use /queue para acompanhar os downloads.",
        parse_mode="Markdown",
    )

    logger.info(
        "Playlist enviada | url=%s | songs=%s | result=%s",
        url,
        len(songs),
        result,
    )


# ============================================================
# /download
# ============================================================

async def download_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ Informe a URL da música.\n\n"
            "Exemplo:\n"
            "`/download https://open.spotify.com/track/...`",
            parse_mode="Markdown",
        )

        return

    url = extract_url(
        " ".join(context.args)
    )

    if not url:

        await update.message.reply_text(
            "❌ Não encontrei uma URL válida."
        )

        return

    await download_single(
        update,
        url,
    )


# ============================================================
# /playlist
# ============================================================

async def playlist_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_authorized(update):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ Informe a URL da playlist.\n\n"
            "Exemplo:\n"
            "`/playlist https://open.spotify.com/playlist/...`",
            parse_mode="Markdown",
        )

        return

    url = extract_url(
        " ".join(context.args)
    )

    if not url:

        await update.message.reply_text(
            "❌ Não encontrei uma URL válida."
        )

        return

    await process_playlist(
        update,
        url,
    )


# ============================================================
# PROCESSA PLAYLIST
# ============================================================

async def process_playlist(
    update: Update,
    url: str,
):

    message = update.message

    await message.reply_text(
        "🔎 Resolvendo a playlist..."
    )

    try:

        response, resolved = await resolve_url(
            url
        )

        if response.status_code != 200:

            await message.reply_text(
                "❌ Não foi possível resolver a playlist.\n\n"
                f"HTTP {response.status_code}\n"
                f"{truncate(str(resolved), 2000)}"
            )

            return

        songs = get_resolved_songs(
            resolved
        )

        if not songs:

            await message.reply_text(
                "❌ O Downtify não retornou músicas "
                "para essa playlist.\n\n"
                f"Resposta:\n{truncate(str(resolved), 2000)}"
            )

            return

        await download_batch(
            update,
            url,
            songs,
        )

    except Exception as exc:

        logger.exception(
            "Erro ao processar playlist"
        )

        await message.reply_text(
            "❌ *Erro ao processar playlist*\n\n"
            f"{exc}",
            parse_mode="Markdown",
        )


# ============================================================
# URL DIRETA
# ============================================================

async def direct_url(
    update: Update,
    url: str,
):

    if is_playlist_url(url):

        await process_playlist(
            update,
            url,
        )

    else:

        await download_single(
            update,
            url,
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

    text = (
        update.effective_message.text
        or ""
    )

    url = extract_url(text)

    if not url:

        await update.effective_message.reply_text(
            "❓ Não encontrei nenhuma URL.\n\n"
            "Use /help para ver os comandos."
        )

        return

    logger.info(
        "URL recebida | user=%s | chat=%s | thread=%s | url=%s",
        update.effective_user.id,
        update.effective_chat.id,
        update.effective_message.message_thread_id,
        url,
    )

    await direct_url(
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
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status,
        )
    )

    application.add_handler(
        CommandHandler(
            "queue",
            queue,
        )
    )

    application.add_handler(
        CommandHandler(
            "download",
            download_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "playlist",
            playlist_command,
        )
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