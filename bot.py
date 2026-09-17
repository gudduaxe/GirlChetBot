import os
import json
import time

from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

TOKEN = os.getenv("BOT_TOKEN")

GROUP_LINK = "https://t.me/+wWnq9mAxw0o4MGQ1"
CHANNEL_LINK = "https://t.me/storiesoffus"
BOT_GROUP_LINK = "https://t.me/GirlChetBot?startgroup=true"

REMINDER_FILE = "reminders.json"
REMINDER_SECONDS = 24 * 60 * 60

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_data():
    try:
        with open(REMINDER_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"groups": {}, "users": {}}


data = load_data()


def save_data():
    with open(REMINDER_FILE, "w") as f:
        json.dump(data, f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add me in your Group",
                url=BOT_GROUP_LINK,
            )
        ],
        [
            InlineKeyboardButton("📢 Channel", url=CHANNEL_LINK),
            InlineKeyboardButton("👥 Group", url=GROUP_LINK),
        ],
    ]

    await update.message.reply_text(
        "WELCOME\n\n"
        "@GirlChetBot — This is the most complete Bot to help you "
        "manage your groups easily and safely.\n\n"
        "➨ Add me in a group and promote me as Admin.\n\n"
        "Any Updates for JOIN Group and Channel 👇🏻",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    if update.effective_chat.type == "private":
        if chat_id not in data["users"]:
            data["users"][chat_id] = {
                "next_send": time.time() + REMINDER_SECONDS
            }
            save_data()

async def bot_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.my_chat_member
    chat = update.effective_chat

    if not member:
        return

    new_status = member.new_chat_member.status
    chat_id = str(chat.id)

    if new_status in ("member", "administrator"):
        if chat.type in ("group", "supergroup"):
            if chat_id not in data["groups"]:
                data["groups"][chat_id] = {
                    "next_send": time.time() + REMINDER_SECONDS
                }
                save_data()

    elif new_status in ("left", "kicked"):
        if chat_id in data["groups"]:
            del data["groups"][chat_id]
            save_data()


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=(
                "You are a friendly Telegram bot. "
                "Chat naturally and concisely. "
                "If the user speaks Hindi or Hinglish, reply in Hindi/Hinglish. "
                "Be respectful, helpful and safe. "
                "Do not claim to be a human."
            ),
            input=user_text,
        )

        reply = response.output_text or (
            "Sorry bhai, abhi reply generate nahi ho paya."
        )

        await update.message.reply_text(reply)

    except Exception as e:
        print("AI Error:", e)
        await update.message.reply_text(
            "Abhi AI se connection nahi ho pa raha 😅"
        )


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat_id, info in list(data["groups"].items()):
        if now >= info["next_send"]:
            try:
                await context.bot.send_message(
                    chat_id=int(chat_id),
                    text=f"👥 Group Link:\n{GROUP_LINK}",
                )

                data["groups"][chat_id]["next_send"] = (
                    now + REMINDER_SECONDS
                )
                save_data()

            except Exception as e:
                print("Group reminder error:", e)

    for chat_id, info in list(data["users"].items()):
        if now >= info["next_send"]:
            try:
                await context.bot.send_message(
                    chat_id=int(chat_id),
                    text=f"👥 Group Link:\n{GROUP_LINK}",
                )

                data["users"][chat_id]["next_send"] = (
                    now + REMINDER_SECONDS
                )
                save_data()

            except Exception as e:
                print("User reminder error:", e)


async def post_init(application):
    application.job_queue.run_repeating(
        reminder_job,
        interval=60,
        first=1,
    )


request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)

app = (
    Application.builder()
    .token(TOKEN)
    .request(request)
    .post_init(post_init)
    .build()
)

app.add_handler(CommandHandler("start", start))

app.add_handler(
    ChatMemberHandler(
        bot_membership,
        ChatMemberHandler.MY_CHAT_MEMBER,
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat,
    )
)

print("Bot is running...")
app.run_polling()
