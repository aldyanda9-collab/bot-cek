#!/usr/bin/env python3
"""
Telegram Bot - Cek User Bot
Fitur User:
- Wajib join 4 channel
- Cek User ID
- Cek Riwayat Username (1x gratis, selanjutnya langganan)
- Info Bahasa Device
- Cek ID Grup/Channel publik
- Langganan 10k/bulan
Fitur Admin:
- Panel Admin
- Broadcast ke semua user
- Total user
- Aktifkan/nonaktifkan langganan
- Approve/tolak pembayaran
"""

import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from telethon import TelegramClient

# ============================================================
# ⚙️ KONFIGURASI
# ============================================================
BOT_TOKEN = "8085735680:AAF8mG_XA3UJ8-qOv0ObYOtnmOvSDzxFBcw"

ADMIN_IDS = [6551372143]

# Info pembayaran langganan
HARGA_LANGGANAN = "10.000"
NAMA_REKENING   = "SEABANK / 901954431148 NURASIAH"   # ← ganti dengan rekening asli
KONTAK_ADMIN    = "@adminmu"                       # ← ganti username admin

REQUIRED_CHANNELS = [
    {"name": "Lisya Store Jaseb",        "username": "@lisyastorejaseb",        "url": "https://t.me/lisyastorejaseb",        "id": "@lisyastorejaseb"},
    {"name": "Freelance Job Indonesian", "username": "@freelancejobindonesian", "url": "https://t.me/freelancejobindonesian", "id": "@freelancejobindonesian"},
    {"name": "Lisya Gacha OTP",          "username": "@lisyagachaotp",          "url": "https://t.me/lisyagachaotp",          "id": "@lisyagachaotp"},
    {"name": "HYUNGNIM LPMM",            "username": "@HYUNGNIMLPMM",           "url": "https://t.me/HYUNGNIMLPMM",           "id": "@HYUNGNIMLPMM"},
]

DB_FILE = "users_db.json"
# ============================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
telethon_client = TelegramClient(SESSION, API_ID, API_HASH)


# ─────────────────────────────────────────────
# 💾 DATABASE
# ─────────────────────────────────────────────
def load_db() -> dict:
    default = {"users": {}, "pending_payments": {}}
    if not os.path.exists(DB_FILE):
        save_db(default)
        return default
    try:
        with open(DB_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                save_db(default)
                return default
            return json.loads(content)
    except Exception:
        save_db(default)
        return default

def save_db(db: dict):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def get_user(user_id: int) -> dict:
    return load_db()["users"].get(str(user_id), {})

def upsert_user(user_id: int, data: dict):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user_id, "name": "", "username": "", "lang": "",
            "riwayat_trial_used": False, "subscribed": False, "sub_expiry": None,
        }
    db["users"][uid].update(data)
    save_db(db)

def is_subscribed(user_id: int) -> bool:
    u = get_user(user_id)
    if not u.get("subscribed"):
        return False
    expiry = u.get("sub_expiry")
    if expiry and datetime.fromisoformat(expiry) < datetime.now():
        upsert_user(user_id, {"subscribed": False, "sub_expiry": None})
        return False
    return True

def trial_used(user_id: int) -> bool:
    return get_user(user_id).get("riwayat_trial_used", False)

def add_pending_payment(user_id: int, name: str, username: str):
    db = load_db()
    db["pending_payments"][str(user_id)] = {
        "user_id": user_id, "name": name, "username": username,
        "time": datetime.now().isoformat(),
    }
    save_db(db)

def remove_pending_payment(user_id: int):
    db = load_db()
    db["pending_payments"].pop(str(user_id), None)
    save_db(db)

def get_pending_payments() -> dict:
    return load_db().get("pending_payments", {})


# ─────────────────────────────────────────────
# 🔍 QUERY SANGMATA
# ─────────────────────────────────────────────
async def query_sangmata(user_query: str) -> str:
    SANGMATA = "SangMata_beta_bot"
    try:
        await telethon_client.send_message(SANGMATA, f"allhistory {user_query}")
        await asyncio.sleep(4)
        messages = await telethon_client.get_messages(SANGMATA, limit=3)
        raw = ""
        for msg in messages:
            if msg.out:
                continue
            if msg.text:
                raw = msg.text
                break
        if not raw:
            return ""
        lines = raw.split("\n")
        formatted = "👤 <b>Riwayat Akun Telegram</b>\n"
        formatted += "─────────────────────\n"
        names = []
        usernames = []
        in_names = False
        in_usernames = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "History for" in line:
                uid = line.replace("👤", "").replace("History for", "").strip()
                formatted += f"🆔 User ID: <code>{uid}</code>\n"
            elif line.lower().startswith("names"):
                in_names = True
                in_usernames = False
            elif line.lower().startswith("usernames"):
                in_names = False
                in_usernames = True
            elif in_names:
                names.append(line)
            elif in_usernames:
                usernames.append(line)
        if names:
            formatted += f"\n📝 <b>Riwayat Nama ({len(names)}x):</b>\n"
            for n in names:
                formatted += f"  {n}\n"
        if usernames:
            formatted += f"\n📛 <b>Riwayat Username ({len(usernames)}x):</b>\n"
            for u in usernames:
                formatted += f"  {u}\n"
        if not names and not usernames:
            formatted += f"\n{raw}"
        formatted += "\n─────────────────────"
        return formatted
    except Exception as e:
        raise Exception(f"Gagal query SangMata: {e}")


# ─────────────────────────────────────────────
# 🔐 CEK MEMBERSHIP
# ─────────────────────────────────────────────
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list:
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined


# ─────────────────────────────────────────────
# ⌨️ INLINE KEYBOARDS
# ─────────────────────────────────────────────
def kb_join(not_joined: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(f"➕ Join {ch['name']}", url=ch["url"])] for ch in not_joined]
    buttons.append([InlineKeyboardButton("✅ Sudah Join Semua", callback_data="check_join")])
    return InlineKeyboardMarkup(buttons)

def kb_main(is_admin=False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("🆔 Cek User ID", callback_data="menu_userid"),
            InlineKeyboardButton("📋 Riwayat Username", callback_data="menu_riwayat"),
        ],
        [
            InlineKeyboardButton("🌐 Info Bahasa Device", callback_data="menu_bahasa"),
            InlineKeyboardButton("👥 Cek ID Grup/Channel", callback_data="menu_grupid"),
        ],
        [InlineKeyboardButton("💎 Status Langganan", callback_data="menu_langganan")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("👑 Panel Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)

def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_menu")]])

def kb_admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("👥 Total User", callback_data="admin_total"),
        ],
        [
            InlineKeyboardButton("💳 Approve Bayar", callback_data="admin_payments"),
            InlineKeyboardButton("✅ Aktifkan User", callback_data="admin_activate"),
        ],
        [InlineKeyboardButton("❌ Nonaktifkan User", callback_data="admin_deactivate")],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_menu")],
    ])

def kb_langganan(subscribed: bool) -> InlineKeyboardMarkup:
    if subscribed:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="back_menu")]])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Bayar Rp{HARGA_LANGGANAN}/bln", callback_data="langganan_bayar")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_menu")],
    ])


# ─────────────────────────────────────────────
# 📌 /start
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    not_joined = await check_membership(user.id, context)
    if not_joined:
        text = (
            f"👋 Halo <b>{user.first_name}</b>!\n\n"
            "🔐 Wajib join channel berikut untuk menggunakan bot:\n\n"
        )
        for i, ch in enumerate(not_joined, 1):
            text += f"  {i}. {ch['name']} — <code>{ch['username']}</code>\n"
        text += "\nJoin dulu lalu tekan ✅"
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb_join(not_joined))
    else:
        upsert_user(user.id, {
            "id": user.id, "name": user.full_name,
            "username": user.username or "", "lang": user.language_code or "",
        })
        await send_main_menu(update, context)


async def send_main_menu(update, context, from_callback=False):
    user = update.effective_user or update.callback_query.from_user
    is_admin = user.id in ADMIN_IDS
    sub = is_subscribed(user.id)
    badge = "👑 " if is_admin else ("💎 " if sub else "")
    text = (
        f"{badge}Halo <b>{user.first_name}</b>! Pilih fitur:\n\n"
        "🆔 <b>Cek User ID</b> — Cek ID kamu atau user lain\n"
        "📋 <b>Riwayat Username</b> — Riwayat perubahan nama\n"
        "🌐 <b>Info Bahasa Device</b> — Bahasa Telegram kamu\n"
        "👥 <b>Cek ID Grup/Channel</b> — Cek ID grup/channel\n"
        "💎 <b>Status Langganan</b> — Kelola langganan"
    )
    if is_admin:
        text += "\n👑 <b>Panel Admin</b> — Kelola bot"
    if from_callback:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb_main(is_admin))
        except Exception:
            await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb_main(is_admin))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb_main(is_admin))


# ─────────────────────────────────────────────
# 📌 CALLBACK HANDLER
# ─────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    is_admin = user.id in ADMIN_IDS

    # ── Cek join ──
    if data == "check_join":
        not_joined = await check_membership(user.id, context)
        if not_joined:
            text = "⚠️ Masih ada yang belum di-join:\n\n"
            for i, ch in enumerate(not_joined, 1):
                text += f"  {i}. {ch['name']} — <code>{ch['username']}</code>\n"
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb_join(not_joined))
        else:
            upsert_user(user.id, {
                "id": user.id, "name": user.full_name,
                "username": user.username or "", "lang": user.language_code or "",
            })
            await send_main_menu(update, context, from_callback=True)
        return

    # ── Guard membership ──
    if not is_admin:
        not_joined = await check_membership(user.id, context)
        if not_joined:
            await query.edit_message_text("🔐 Join semua channel dulu!", reply_markup=kb_join(not_joined))
            return

    # ── Back menu ──
    if data == "back_menu":
        context.user_data["waiting_for"] = None
        await send_main_menu(update, context, from_callback=True)

    # ══ LANGGANAN ══
    elif data == "menu_langganan":
        sub = is_subscribed(user.id)
        u = get_user(user.id)
        expiry = u.get("sub_expiry")
        if sub and expiry:
            exp_str = datetime.fromisoformat(expiry).strftime("%d %B %Y")
            text = (
                "💎 <b>Status Langganan</b>\n\n"
                f"✅ Status  : <b>Aktif</b>\n"
                f"📅 Hingga : <b>{exp_str}</b>\n\n"
                "Nikmati akses penuh Riwayat Username! 🎉"
            )
        else:
            used = trial_used(user.id)
            text = (
                "💎 <b>Status Langganan</b>\n\n"
                f"❌ Status : <b>Tidak Aktif</b>\n"
                f"🎁 Trial  : {'Sudah digunakan' if used else 'Belum digunakan (1x gratis)'}\n\n"
                f"📦 Harga : <b>Rp{HARGA_LANGGANAN}/bulan</b>\n"
                f"🏦 Bayar ke: <code>{NAMA_REKENING}</code>"
            )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb_langganan(sub))

    elif data == "langganan_bayar":
        context.user_data["waiting_for"] = "bukti_bayar"
        await query.edit_message_text(
            f"💳 <b>Pembayaran Langganan</b>\n\n"
            f"Transfer <b>Rp{HARGA_LANGGANAN}</b> ke:\n"
            f"🏦 <code>{NAMA_REKENING}</code>\n\n"
            "Setelah transfer, kirim <b>screenshot bukti</b> ke sini.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="back_menu")]])
        )

    # ══ CEK USER ID ══
    elif data == "menu_userid":
        await query.edit_message_text(
            "🆔 <b>Cek User ID</b>\n\nPilih:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 ID Saya", callback_data="userid_self"),
                 InlineKeyboardButton("🔍 Cek @username Lain", callback_data="userid_other")],
                [InlineKeyboardButton("🔙 Kembali", callback_data="back_menu")],
            ])
        )

    elif data == "userid_self":
        lang = user.language_code or "Tidak diketahui"
        await query.edit_message_text(
            "🆔 <b>User ID Kamu</b>\n\n"
            f"👤 Nama     : <b>{user.full_name}</b>\n"
            f"🆔 User ID  : <code>{user.id}</code>\n"
            f"📛 Username : <code>@{user.username or '(tidak ada)'}</code>\n"
            f"🌐 Bahasa   : <code>{lang}</code>\n"
            f"🤖 Bot?     : {'Ya' if user.is_bot else 'Tidak'}\n\n"
            "💡 <i>User ID bersifat permanen.</i>",
            parse_mode="HTML", reply_markup=kb_back()
        )

    elif data == "userid_other":
        context.user_data["waiting_for"] = "userid_other"
        await query.edit_message_text(
            "🔍 Kirim <b>@username</b> yang ingin dicek:\n\n<i>Contoh: @durov</i>",
            parse_mode="HTML", reply_markup=kb_back()
        )

    # ══ RIWAYAT USERNAME ══
    elif data == "menu_riwayat":
        sub = is_subscribed(user.id)
        used = trial_used(user.id)
        if not sub and used:
            await query.edit_message_text(
                "🔒 <b>Fitur Terkunci</b>\n\n"
                "Trial gratis sudah digunakan.\n\n"
                f"💎 Berlangganan Rp{HARGA_LANGGANAN}/bulan untuk akses tak terbatas.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"💳 Bayar Rp{HARGA_LANGGANAN}/bln", callback_data="langganan_bayar")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data="back_menu")],
                ])
            )
            return
        if not sub:
            upsert_user(user.id, {"riwayat_trial_used": True})
        badge = "🎁 Trial gratis" if not sub else "💎 Langganan aktif"
        context.user_data["waiting_for"] = "format_riwayat"
        await query.edit_message_text(
            f"📋 <b>Cek Riwayat Username</b>\n\n"
            f"{badge}\n\n"
            "Kirim <b>User ID</b> (angka) yang ingin dicek:\n\n"
            "<i>Contoh: 6084856206</i>\n\n"
            "💡 Tidak tahu ID? Gunakan fitur Cek User ID dulu.",
            parse_mode="HTML", reply_markup=kb_back()
        )

    # ══ BAHASA ══
    elif data == "menu_bahasa":
        lang = user.language_code or "Tidak terdeteksi"
        lang_map = {
            "id": "🇮🇩 Indonesia", "en": "🇺🇸 English", "ar": "🇸🇦 Arabic",
            "zh": "🇨🇳 Chinese", "ru": "🇷🇺 Russian", "es": "🇪🇸 Spanish",
            "fr": "🇫🇷 French", "de": "🇩🇪 German", "pt": "🇧🇷 Portuguese",
            "tr": "🇹🇷 Turkish", "ja": "🇯🇵 Japanese", "ko": "🇰🇷 Korean",
            "ms": "🇲🇾 Malay", "hi": "🇮🇳 Hindi", "nl": "🇳🇱 Dutch",
        }
        lang_label = lang_map.get(lang, f"🌐 {lang.upper()}" if lang != "Tidak terdeteksi" else lang)
        await query.edit_message_text(
            "🌐 <b>Info Bahasa Device</b>\n\n"
            f"👤 User        : <b>{user.full_name}</b>\n"
            f"🆔 User ID     : <code>{user.id}</code>\n"
            f"🌍 Kode Bahasa : <code>{lang}</code>\n"
            f"🏷️ Bahasa      : <b>{lang_label}</b>\n\n"
            "💡 <i>Diambil dari pengaturan bahasa Telegram kamu.</i>",
            parse_mode="HTML", reply_markup=kb_back()
        )

    # ══ GRUP/CHANNEL ══
    elif data == "menu_grupid":
        context.user_data["waiting_for"] = "grupid"
        await query.edit_message_text(
            "👥 <b>Cek ID Grup / Channel</b>\n\n"
            "Kirim <b>@username</b> grup atau channel:\n\n"
            "<i>Contoh: @telegram</i>\n\n"
            "📌 Hanya bisa cek yang <b>publik</b>.",
            parse_mode="HTML", reply_markup=kb_back()
        )

    # ══ ADMIN PANEL ══
    elif data == "admin_panel":
        if not is_admin:
            await query.answer("⛔ Bukan admin!", show_alert=True)
            return
        total = len(load_db().get("users", {}))
        pending = len(get_pending_payments())
        await query.edit_message_text(
            f"👑 <b>Panel Admin</b>\n\n"
            f"👥 Total user      : <b>{total}</b>\n"
            f"💳 Pending bayar   : <b>{pending}</b>",
            parse_mode="HTML", reply_markup=kb_admin_panel()
        )

    elif data == "admin_total":
        if not is_admin: return
        users = load_db().get("users", {})
        aktif = sum(1 for u in users.values() if is_subscribed(int(u["id"])))
        await query.edit_message_text(
            f"👥 <b>Total Pengguna</b>\n\n"
            f"📊 Total terdaftar    : <b>{len(users)} user</b>\n"
            f"💎 Berlangganan       : <b>{aktif} user</b>\n"
            f"👤 Tidak berlangganan : <b>{len(users)-aktif} user</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")]])
        )

    elif data == "admin_broadcast":
        if not is_admin: return
        context.user_data["waiting_for"] = "broadcast"
        await query.edit_message_text(
            "📢 <b>Broadcast Pesan</b>\n\n"
            "Ketik pesan yang ingin dikirim ke semua user.\n"
            "Support HTML: <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>\n\n"
            "Kirim sekarang atau /batal.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_panel")]])
        )

    elif data == "admin_payments":
        if not is_admin: return
        pending = get_pending_payments()
        if not pending:
            await query.edit_message_text(
                "💳 <b>Approve Pembayaran</b>\n\n✅ Tidak ada yang menunggu.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")]])
            )
        else:
            text = "💳 <b>Pembayaran Menunggu:</b>\n\n"
            buttons = []
            for uid, info in pending.items():
                waktu = datetime.fromisoformat(info["time"]).strftime("%d/%m %H:%M")
                text += f"• <b>{info['name']}</b> (@{info['username'] or '-'}) ID: <code>{uid}</code> [{waktu}]\n"
                buttons.append([
                    InlineKeyboardButton(f"✅ {info['name']}", callback_data=f"approve_{uid}"),
                    InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{uid}"),
                ])
            buttons.append([InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")])
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("approve_"):
        if not is_admin: return
        uid = int(data.split("_")[1])
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        upsert_user(uid, {"subscribed": True, "sub_expiry": expiry})
        remove_pending_payment(uid)
        exp_str = datetime.fromisoformat(expiry).strftime("%d %B %Y")
        try:
            await context.bot.send_message(uid,
                f"✅ <b>Pembayaran Disetujui!</b>\n\nLangganan aktif hingga <b>{exp_str}</b> 💎",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.answer(f"✅ User {uid} diaktifkan!", show_alert=True)
        pending = get_pending_payments()
        if pending:
            text = "💳 <b>Pembayaran Menunggu:</b>\n\n"
            buttons = []
            for puid, info in pending.items():
                waktu = datetime.fromisoformat(info["time"]).strftime("%d/%m %H:%M")
                text += f"• <b>{info['name']}</b> ID: <code>{puid}</code> [{waktu}]\n"
                buttons.append([
                    InlineKeyboardButton(f"✅ {info['name']}", callback_data=f"approve_{puid}"),
                    InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{puid}"),
                ])
            buttons.append([InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")])
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.edit_message_text(
                "💳 ✅ Semua pembayaran sudah diproses.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")]])
            )

    elif data.startswith("reject_"):
        if not is_admin: return
        uid = int(data.split("_")[1])
        remove_pending_payment(uid)
        try:
            await context.bot.send_message(uid,
                f"❌ <b>Pembayaran Ditolak</b>\n\nBukti tidak valid. Hubungi {KONTAK_ADMIN}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.answer("❌ Ditolak.", show_alert=True)
        await query.edit_message_text(
            "❌ Pembayaran ditolak.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")]])
        )

    elif data == "admin_activate":
        if not is_admin: return
        context.user_data["waiting_for"] = "admin_activate_id"
        await query.edit_message_text(
            "✅ <b>Aktifkan Langganan</b>\n\nKirim <b>User ID</b> yang ingin diaktifkan:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_panel")]])
        )

    elif data == "admin_deactivate":
        if not is_admin: return
        context.user_data["waiting_for"] = "admin_deactivate_id"
        await query.edit_message_text(
            "❌ <b>Nonaktifkan Langganan</b>\n\nKirim <b>User ID</b> yang ingin dinonaktifkan:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_panel")]])
        )


# ─────────────────────────────────────────────
# 📌 MESSAGE HANDLER
# ─────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg_text = update.message.text.strip() if update.message.text else ""
    is_admin = user.id in ADMIN_IDS
    waiting = context.user_data.get("waiting_for")

    if msg_text == "/batal":
        context.user_data["waiting_for"] = None
        await send_main_menu(update, context)
        return

    # ── BROADCAST ──
    if waiting == "broadcast" and is_admin:
        context.user_data["waiting_for"] = None
        user_ids = [int(uid) for uid in load_db().get("users", {}).keys()]
        berhasil = gagal = 0
        status_msg = await update.message.reply_text(f"⏳ Mengirim ke <b>{len(user_ids)} user</b>...", parse_mode="HTML")
        for uid in user_ids:
            try:
                await context.bot.send_message(uid, f"📢 <b>Pesan dari Admin</b>\n{'─'*25}\n\n{msg_text}", parse_mode="HTML")
                berhasil += 1
            except Exception:
                gagal += 1
        await status_msg.edit_text(
            f"✅ <b>Broadcast Selesai!</b>\n\n✅ Berhasil: <b>{berhasil}</b>\n❌ Gagal: <b>{gagal}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Admin", callback_data="admin_panel")]])
        )
        return

    # ── ADMIN AKTIFKAN ──
    if waiting == "admin_activate_id" and is_admin:
        context.user_data["waiting_for"] = None
        try:
            uid = int(msg_text)
            expiry = (datetime.now() + timedelta(days=30)).isoformat()
            upsert_user(uid, {"subscribed": True, "sub_expiry": expiry})
            exp_str = datetime.fromisoformat(expiry).strftime("%d %B %Y")
            await update.message.reply_text(
                f"✅ Langganan <code>{uid}</code> aktif hingga <b>{exp_str}</b>.",
                parse_mode="HTML", reply_markup=kb_admin_panel()
            )
            try:
                await context.bot.send_message(uid,
                    f"✅ <b>Langganan Diaktifkan!</b>\n\nAktif hingga <b>{exp_str}</b> 💎",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ User ID tidak valid.")
        return

    # ── ADMIN NONAKTIFKAN ──
    if waiting == "admin_deactivate_id" and is_admin:
        context.user_data["waiting_for"] = None
        try:
            uid = int(msg_text)
            upsert_user(uid, {"subscribed": False, "sub_expiry": None})
            await update.message.reply_text(
                f"❌ Langganan <code>{uid}</code> dinonaktifkan.",
                parse_mode="HTML", reply_markup=kb_admin_panel()
            )
            try:
                await context.bot.send_message(uid, "❌ <b>Langganan Dinonaktifkan</b>\n\nLangganan kamu telah dinonaktifkan.", parse_mode="HTML")
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ User ID tidak valid.")
        return

    # ── Guard membership ──
    if not is_admin:
        not_joined = await check_membership(user.id, context)
        if not_joined:
            await update.message.reply_text("🔐 Join semua channel dulu!", reply_markup=kb_join(not_joined))
            return

    if not waiting:
        await send_main_menu(update, context)
        return

    username = msg_text if msg_text.startswith("@") else f"@{msg_text}"
    clean = username.replace("@", "")

    # ── CEK USER ID LAIN ──
    if waiting == "userid_other":
        context.user_data["waiting_for"] = None
        wait_msg = await update.message.reply_text("⏳ Mencari...")
        try:
            entity = await telethon_client.get_entity(username)
            full_name = ""
            if hasattr(entity, "first_name"):
                full_name = (entity.first_name or "") + " " + (entity.last_name or "")
                full_name = full_name.strip()
            elif hasattr(entity, "title"):
                full_name = entity.title
            uname = f"@{entity.username}" if entity.username else "(tidak ada)"
            tipe = "👤 User" if hasattr(entity, "first_name") else "👥 Grup/Channel"
            is_bot_entity = getattr(entity, "bot", False)
            await wait_msg.edit_text(
                f"🆔 <b>Informasi User</b>\n\n"
                f"👤 Nama     : <b>{full_name}</b>\n"
                f"🆔 User ID  : <code>{entity.id}</code>\n"
                f"📛 Username : <code>{uname}</code>\n"
                f"🏷️ Tipe     : {tipe}\n"
                f"🤖 Bot?     : {'Ya' if is_bot_entity else 'Tidak'}\n\n"
                "💡 <i>User ID bersifat permanen.</i>",
                parse_mode="HTML", reply_markup=kb_back()
            )
        except Exception:
            await wait_msg.edit_text(
                f"❌ <b>User tidak ditemukan!</b>\n\n"
                f"<code>{username}</code> tidak bisa dicek.\n"
                "Pastikan username benar dan akun masih aktif.",
                parse_mode="HTML", reply_markup=kb_back()
            )

    # ── RIWAYAT USERNAME ──
    elif waiting == "format_riwayat":
        context.user_data["waiting_for"] = None
        query_input = msg_text.strip().replace("@", "")
        wait_msg = await update.message.reply_text("⏳ Mengambil riwayat...")
        try:
            result = await query_sangmata(query_input)
            if result:
                await wait_msg.edit_text(result, parse_mode="HTML", reply_markup=kb_back())
            else:
                await wait_msg.edit_text(
                    f"❌ Tidak ditemukan riwayat untuk <code>{query_input}</code>\n\n"
                    "Kemungkinan akun belum pernah terdata.",
                    parse_mode="HTML", reply_markup=kb_back()
                )
        except Exception as e:
            await wait_msg.edit_text(f"❌ Gagal: {str(e)}", reply_markup=kb_back())

    # ── GRUP/CHANNEL ──
    elif waiting == "grupid":
        context.user_data["waiting_for"] = None
        try:
            chat = await context.bot.get_chat(username)
            tipe = {"group": "👥 Grup", "supergroup": "👥 Supergroup", "channel": "📢 Channel"}.get(chat.type, chat.type)
            await update.message.reply_text(
                f"👥 <b>Informasi Grup/Channel</b>\n\n"
                f"📌 Nama     : <b>{chat.title}</b>\n"
                f"🆔 ID       : <code>{chat.id}</code>\n"
                f"📛 Username : <code>{username}</code>\n"
                f"🏷️ Tipe     : {tipe}",
                parse_mode="HTML", reply_markup=kb_back()
            )
        except Exception:
            await update.message.reply_text(
                f"❌ <code>{username}</code> tidak ditemukan.",
                parse_mode="HTML", reply_markup=kb_back()
            )
    else:
        await send_main_menu(update, context)


# ─────────────────────────────────────────────
# 📌 PHOTO HANDLER — bukti pembayaran
# ─────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    waiting = context.user_data.get("waiting_for")

    if not is_admin:
        not_joined = await check_membership(user.id, context)
        if not_joined:
            await update.message.reply_text("🔐 Join semua channel dulu!", reply_markup=kb_join(not_joined))
            return

    if waiting == "bukti_bayar":
        context.user_data["waiting_for"] = None
        add_pending_payment(user.id, user.full_name, user.username or "")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
                await context.bot.send_message(
                    admin_id,
                    f"💳 <b>Bukti Pembayaran Baru!</b>\n\n"
                    f"👤 Nama : <b>{user.full_name}</b>\n"
                    f"📛 Username : @{user.username or '-'}\n"
                    f"🆔 ID : <code>{user.id}</code>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}"),
                         InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{user.id}")],
                    ])
                )
            except Exception:
                pass
        await update.message.reply_text(
            "✅ <b>Bukti diterima!</b>\n\nAdmin akan verifikasi segera. Kamu akan dapat notifikasi. 🎉",
            parse_mode="HTML", reply_markup=kb_back()
        )
    else:
        await update.message.reply_text("📷 Gunakan menu untuk fitur bot.", reply_markup=kb_main(is_admin))


# ─────────────────────────────────────────────
# 📌 FORWARD HANDLER
# ─────────────────────────────────────────────
async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    if not is_admin:
        not_joined = await check_membership(user.id, context)
        if not_joined:
            await update.message.reply_text("🔐 Join semua channel dulu!", reply_markup=kb_join(not_joined))
            return
    msg = update.message
    if msg.forward_from_chat:
        chat = msg.forward_from_chat
        tipe = {"group": "👥 Grup", "supergroup": "👥 Supergroup", "channel": "📢 Channel"}.get(chat.type, chat.type)
        text = (
            f"📢 <b>Info dari Forward</b>\n\n"
            f"📌 Nama : <b>{chat.title}</b>\n"
            f"🆔 ID   : <code>{chat.id}</code>\n"
            f"🏷️ Tipe : {tipe}\n"
        )
        if chat.username:
            text += f"🔗 Link : @{chat.username}\n"
        await msg.reply_text(text, parse_mode="HTML", reply_markup=kb_back())
    elif msg.forward_from:
        fwd = msg.forward_from
        await msg.reply_text(
            f"👤 <b>Info User Forward</b>\n\n"
            f"📌 Nama : <b>{fwd.full_name}</b>\n"
            f"🆔 ID   : <code>{fwd.id}</code>\n"
            f"📛 Username : @{fwd.username or '-'}",
            parse_mode="HTML", reply_markup=kb_back()
        )


# ─────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────
async def main():
    await telethon_client.start(phone=PHONE)
    logger.info("Telethon terhubung!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
    app.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, forward_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, message_handler))

    logger.info("Bot berjalan...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await telethon_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())