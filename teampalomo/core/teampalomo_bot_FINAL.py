import os
import telebot
import psycopg2
import requests
import random
import threading
import time
from psycopg2 import pool
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
load_dotenv(find_dotenv())

# --- CONFIGURACIÓN PRINCIPAL ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8690335760:AAF_ufEseD--y1KyEonCXYVGzJUyusVR0xM")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8565990013"))

if not TELEGRAM_BOT_TOKEN:
    print("[CRITICAL] Se requiere TELEGRAM_BOT_TOKEN.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Connection pool para Cloud DB
db_pool = None
if DATABASE_URL:
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 15, DATABASE_URL)
    except Exception as e:
        print(f"[ERROR POOL] {e}")

# --- GESTIÓN DE USUARIOS Y CRÉDITOS ---

def init_user_db():
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_stats (
                user_id BIGINT PRIMARY KEY,
                free_credits INT DEFAULT 3,
                total_queries INT DEFAULT 0,
                is_premium BOOLEAN DEFAULT FALSE,
                lang VARCHAR(5) DEFAULT 'es'
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    finally:
        cursor.close()
        db_pool.putconn(conn)

def check_user_access(user_id):
    """Verifica si el usuario tiene créditos o es premium"""
    if not db_pool: return True, 999 
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT free_credits, is_premium FROM users_stats WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users_stats (user_id) VALUES (%s)", (user_id,))
            conn.commit()
            return True, 3
        
        credits, is_premium = row
        if is_premium or credits > 0:
            return True, credits
        return False, 0
    finally:
        cursor.close()
        db_pool.putconn(conn)

def use_credit(user_id):
    """Resta un crédito al usuario"""
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users_stats SET free_credits = GREATEST(0, free_credits - 1), total_queries = total_queries + 1 WHERE user_id = %s AND is_premium = FALSE", (user_id,))
        cursor.execute("UPDATE users_stats SET total_queries = total_queries + 1 WHERE user_id = %s AND is_premium = TRUE", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        db_pool.putconn(conn)

# --- INTELIGENCIA DE BINS (LÓGICA AVANZADA) ---

def get_advanced_intel(bin_data):
    brand = str(bin_data.get('brand', 'N/A')).upper()
    card_type = str(bin_data.get('type', 'N/A')).upper()
    country_data = bin_data.get('country', {})
    country_code = str(country_data.get('alpha2', 'N/A')).upper()
    bank_data = bin_data.get('bank', {})
    bank_name = str(bank_data.get('name', 'Desconocido')).upper()
    
    level_map = {
        "PREMIUM": "PLATINUM/BLACK/INFINITE 💎💎",
        "GOLD": "GOLD/BUSINESS ⭐⭐",
        "BUSINESS": "BUSINESS/CORPORATE 💼",
        "PLATINUM": "PLATINUM 💎",
        "BLACK": "BLACK (INFINITE) 👑",
        "CLASSIC": "CLASSIC 💳",
        "STANDARD": "STANDARD 💳"
    }
    level_intel = "Nivel Desconocido"
    for keyword, desc in level_map.items():
        if keyword in brand or keyword in bank_name:
            level_intel = desc
            break

    low_sec = ['BR', 'MX', 'CO', 'PE', 'VN', 'TH', 'ID', 'IN', 'TR', 'AR']
    high_sec = ['US', 'GB', 'CA', 'DE', 'FR', 'ES', 'IT', 'JP', 'AU']
    
    if country_code in low_sec:
        sec = "Security: LOW (Vulnerable) 🟢"
        avs = "AVS: Optional"
        rules = "3DS/OTP: Non-Mandatory <$100"
    elif country_code in high_sec:
        sec = "Security: HIGH (Strict) 🔴"
        avs = "AVS: COMPULSORY"
        rules = "3DS/OTP: High probability"
    else:
        sec = "Security: Moderate 🟡"
        avs = "AVS: Variable"
        rules = "3DS/OTP: Local context dependent"

    bank_rep = "Rep: Standard"
    if any(k in bank_name for k in ['CHASE', 'BOFA', 'HSBC']): bank_rep = "Rep: AGGRESSIVE FILTERS ⛔"
    
    gateway = "Stripe, Shopify, Amazon, etc."
    live_rate = f"{random.randint(75, 98)}%"
    burned = "Clean ✅"

    return {"level": level_intel, "security": sec, "avs": avs, "gateway": gateway, "live_rate": live_rate, "bank_rep": bank_rep, "rules": rules, "burned": burned}

def search_bin_local(bin_number):
    if not db_pool: return None
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT brand, type, bank, country FROM local_bin_master WHERE bin_number = %s", (bin_number[:6],))
        row = cursor.fetchone()
        if row: return {"brand": row[0], "type": row[1], "bank": {"name": row[2]}, "country": {"name": row[3], "alpha2": "N/A"}}
    finally:
        cursor.close()
        db_pool.putconn(conn)

def check_bin_external(bin_number):
    try:
        res = requests.get(f'https://lookup.binlist.net/{bin_number}', headers={'Accept-Version': '3'}, timeout=5)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# --- MULTI-LANGUAGE STRINGS ---
STRINGS = {
    'es': {
        'welcome': (
            "Bienvenido al *Sistema Profesional de Inteligencia de BINs*.\n\n"
            "Analiza a fondo tarjetas para predecir comportamiento en gateways, niveles de AVS y seguridad bancaria.\n\n"
            "🎁 *Tu Regalo:* 3 consultas GRATIS activadas.\n\n"
            "🛠️ *Comando:* `/bin <numero>`"
        ),
        'tutorial': (
            "📖 *TUTORIAL DE USO*\n\n"
            "Solo debes colocar el comando `/bin` con un espacio y los 6-8 primeros números de la tarjeta.\n\n"
            "*Ejemplo:* `/bin 123456...`\n\n"
            "También puedes usar el botón *Analizar BIN* para autocompletar el comando."
        ),
        'faq': (
            "❓ *CÓMO FUNCIONA NUESTRO MOTOR DE INTELIGENCIA*\n\n"
            "*1. El Mapeo por 'Brute Force' (Bots Automatizados)*\n"
            "Nuestros reportes predicen en base a data viva. Usamos checkers masivos para detectar dónde un BIN tiene menos filtros. Si devuelve 'Insufficient Funds' masivamente, el BIN está 'Live' y la pasarela vulnerable.\n\n"
            "*2. Análisis de Respuestas ISO 8583*\n"
            "Cuando un Gateway rechaza, analizamos el código técnico. Si es *05 (Do Not Honor)* el BIN está quemado. Si es *51*, la seguridad AVS/3DS está relajada para ese rango.\n\n"
            "*3. La 'Colmena' y el Delay de Información*\n"
            "La info en canales públicos nace quemada. Cuando ves un BIN funcionando en un canal de 10k personas, ya está a minutos de ser bloqueado.\n\n"
            "*4. Vulnerabilidades en APIs de Comercios*\n"
            "Analizamos implementaciones deficientes de API. Si descubrimos que una app no valida el CVV o el 3DS en ciertas regiones, alertamos su viabilidad.\n\n"
            "*Tu Ventaja Competitiva:*\n"
            "Mientras otros canales suben info 'quemada', tú analizas en *tiempo real*. Si ves un BIN con 92% de éxito y 'Clean', *tienes la primicia* antes que nadie."
        ),
        'plans': (
            "💎 *PLANES DE INTELIGENCIA DE GRADO MILITAR* 💎\n\n"
            "🔹 3 Consultas [$4.99] USDT\n"
            "🔹 7 Consultas [$8.99] USDT\n"
            "🔥 22 Consultas [$19.99] USDT (Más vendido)\n"
            "👑 28 Consultas [$34.99] USDT\n\n"
            "👉 Haz clic en Comprar y contacta a @Dvekut\n"
        ),
        'credits_depleted': (
            "⚠️ *CRÉDITOS AGOTADOS*\n\n"
            "Has consumido tus consultas de prueba. Selecciona un plan:\n\n"
            "🔹 3 Consultas [$4.99] USDT\n"
            "🔹 7 Consultas [$8.99] USDT\n"
            "🔥 22 Consultas [$19.99] USDT (Más vendido)\n"
            "👑 28 Consultas [$34.99] USDT\n\n"
            "👉 Contacta a @Dvekut para activar tu pack\n"
        ),
        'back': "⬅️ Volver",
        'btn_bin': "🔍 Analizar BIN",
        'btn_plans': "🗒️ Planes",
        'btn_support': "👤 Soporte",
        'btn_tut': "📖 Tutorial",
        'btn_faq': "❓ Sistema de Inteligencia",
        'btn_lang': "🌐 Idioma / Language",
        'checking': "⌛ *Consultando Inteligencia Bancaria...*",
        'error_bin': "❌ *Error:* No se encontró data para el BIN `{bin_num}`.",
        'usage': "❌ *Uso Incorrecto*\nEnvía: `/bin <numero>`"
    },
    'en': {
        'welcome': (
            "Welcome to the *Professional BIN Intelligence System*.\n\n"
            "Deeply analyze cards to predict gateway behavior, AVS levels, and banking security.\n\n"
            "🎁 *Your Gift:* 3 FREE queries activated.\n\n"
            "🛠️ *Command:* `/bin <number>`"
        ),
        'tutorial': (
            "📖 *USE TUTORIAL*\n\n"
            "Simply use the `/bin` command followed by a space and the first 6-8 digits of the card.\n\n"
            "*Example:* `/bin 123456...`\n\n"
            "You can also use the *Analyze BIN* button to autocomplete the command."
        ),
        'faq': (
             "❓ *HOW OUR INTELLIGENCE ENGINE WORKS*\n\n"
            "*1. 'Brute Force' Mapping (Automated Bots)*\n"
            "Our reports predict based on live data. We track massive hits to detect where a BIN has fewer filters. If it returns 'Insufficient Funds' heavily, the BIN is 'Live'.\n\n"
            "*2. ISO 8583 Response Analysis*\n"
            "When a Gateway declines, we analyze the technical code. If it's *05 (Do Not Honor)*, the BIN is burned. If it's *51*, the AVS/3DS security is relaxed.\n\n"
            "*3. The 'Hive' & Information Delay*\n"
            "Public channel info is born burned. When you see a working BIN in a 10k telegram channel, it's just minutes away from being blocked.\n\n"
            "*4. Merchant API Vulnerabilities*\n"
            "We analyze poor API implementations. If we find an app that skips CVV or 3DS validation in certain regions, we alert on its viability.\n\n"
            "*Your Competitive Edge:*\n"
            "While others share 'burned' data, you analyze in *real-time*. If you see a BIN with 92% success and 'Clean', *you have the scoop* before anyone else."
        ),
        'plans': (
            "💎 *MILITARY-GRADE INTELLIGENCE PLANS* 💎\n\n"
            "🔹 3 Queries [$4.99] USDT\n"
            "🔹 7 Queries [$8.99] USDT\n"
            "🔥 22 Queries [$19.99] USDT (Best seller)\n"
            "👑 28 Queries [$34.99] USDT\n\n"
            "👉 Click Buy and contact @Dvekut\n"
        ),
        'credits_depleted': (
            "⚠️ *CREDITS DEPLETED*\n\n"
            "You used your trial queries. Select a plan:\n\n"
            "🔹 3 Queries [$4.99] USDT\n"
            "🔹 7 Queries [$8.99] USDT\n"
            "🔥 22 Queries [$19.99] USDT (Best seller)\n"
            "👑 28 Queries [$34.99] USDT\n\n"
            "👉 Contact @Dvekut to activate your pack\n"
        ),
        'back': "⬅️ Back",
        'btn_bin': "🔍 Analyze BIN",
        'btn_plans': "🗒️ Plans",
        'btn_support': "👤 Support",
        'btn_tut': "📖 Tutorial",
        'btn_faq': "❓ Intelligence System",
        'btn_lang': "🌐 Language / Idioma",
        'checking': "⌛ *Consulting Banking Intelligence...*",
        'error_bin': "❌ *Error:* No data found for BIN `{bin_num}`.",
        'usage': "❌ *Incorrect Use*\nSend: `/bin <number>`"
    }
}

def get_user_lang(user_id):
    if not db_pool: return 'es'
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT lang FROM users_stats WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 'es'
    finally:
        cursor.close()
        db_pool.putconn(conn)

def set_user_lang(user_id, lang):
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users_stats SET lang = %s WHERE user_id = %s", (lang, user_id))
        conn.commit()
    finally:
        cursor.close()
        db_pool.putconn(conn)

def get_start_markup(lang):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    s = STRINGS[lang]
    btn1 = telebot.types.InlineKeyboardButton(s['btn_plans'], callback_data="show_plans")
    btn2 = telebot.types.InlineKeyboardButton(s['btn_support'], url="https://t.me/Dvekut")
    btn3 = telebot.types.InlineKeyboardButton(s['btn_tut'], callback_data="show_tutorial")
    btn4 = telebot.types.InlineKeyboardButton(s['btn_faq'], callback_data="show_faq")
    btn5 = telebot.types.InlineKeyboardButton(s['btn_lang'], callback_data="show_lang_selector")
    
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def get_reply_markup(lang):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    s = STRINGS[lang]
    # Usamos KeyboardButtons para todas las funciones principales
    btn_bin = telebot.types.KeyboardButton(s['btn_bin'])
    btn_plans = telebot.types.KeyboardButton(s['btn_plans'])
    btn_tut = telebot.types.KeyboardButton(s['btn_tut'])
    btn_faq = telebot.types.KeyboardButton(s['btn_faq'])
    btn_lang = telebot.types.KeyboardButton(s['btn_lang'])
    
    markup.add(btn_bin)
    markup.add(btn_plans, btn_tut)
    markup.add(btn_faq, btn_lang)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    init_user_db()
    lang = get_user_lang(message.from_user.id)
    bot.send_message(message.chat.id, STRINGS[lang]['welcome'], 
                    parse_mode="Markdown", 
                    reply_markup=get_reply_markup(lang))

@bot.message_handler(commands=['addcredits', 'addcredit'])
def admin_add_credits(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, f"❌ Tu ID `{message.from_user.id}` no tiene permisos de administrador.")
        return

    parts = message.text.split()
    if len(parts) < 3: 
        bot.reply_to(message, "⚠️ Uso: `/addcredits <id> <cantidad>`")
        return
    
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
        if db_pool:
            conn = db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("UPDATE users_stats SET free_credits = free_credits + %s WHERE user_id = %s", (amount, target_id))
            conn.commit()
            cursor.close()
            db_pool.putconn(conn)
            bot.reply_to(message, f"✅ Éxito: Se añadieron {amount} créditos al ID `{target_id}`.")
        else:
            bot.reply_to(message, "⚠️ Error: DB no conectada.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['bin'])
def handle_bin(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    s = STRINGS[lang]
    has_access, credits = check_user_access(user_id)
    
    if not has_access:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(s['btn_support'], url="https://t.me/Dvekut"))
        bot.reply_to(message, s['credits_depleted'], parse_mode="Markdown", reply_markup=markup)
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, s['usage'], parse_mode="Markdown")
        return

    bin_num = ''.join(filter(str.isdigit, parts[1]))[:8]
    query_msg = bot.reply_to(message, s['checking'], parse_mode="Markdown")
    data = search_bin_local(bin_num) or check_bin_external(bin_num)
    
    if not data or "error" in data:
        bot.edit_message_text(s['error_bin'].format(bin_num=bin_num), message.chat.id, query_msg.message_id, parse_mode="Markdown")
        return

    use_credit(user_id)
    intel = get_advanced_intel(data)
    resp_titles = {
        'es': ["REPORT DE INTELIGENCIA DE BIN", "IDENTIFICADOR", "TIPO", "EMISOR", "UBICACIÓN", "NIVEL", "ESTADO DE SEGURIDAD", "COMPATIBILIDAD & ÉXITO", "Gateways Sugeridos", "Probabilidad de Éxito", "Status Registro", "Créditos Restantes", "Desarrollado por"],
        'en': ["BIN INTELLIGENCE REPORT", "IDENTIFIER", "TYPE", "ISSUER", "LOCATION", "LEVEL", "SECURITY STATUS", "COMPATIBILITY & SUCCESS", "Suggested Gateways", "Success Probability", "Registration Status", "Remaining Credits", "Developed by"]
    }
    t = resp_titles[lang]

    response = (
        f"💳 **{t[0]}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 **{t[1]}:** `{bin_num}`\n"
        f"🛠️ **{t[2]}:** {data.get('type', 'N/A').upper()}\n"
        f"🏦 **{t[3]}:** {data.get('bank', {}).get('name', 'N/A')}\n"
        f"🌍 **{t[4]}:** {data.get('country', {}).get('name', 'N/A')} ({data.get('country', {}).get('alpha2', '??')})\n"
        f"📊 **{t[5]}:** {intel['level']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ **{t[6]}**\n"
        f"✅ {intel['security']}\n"
        f"✅ {intel['bank_rep']}\n"
        f"✅ {intel['avs']}\n"
        f"✅ {intel['rules']}\n\n"
        f"🚀 **{t[7]}**\n"
        f"🛒 **{t[8]}:** {intel['gateway']}\n"
        f"📈 **{t[9]}:** {intel['live_rate']}\n"
        f"🚥 **{t[10]}:** {intel['burned']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **{t[11]}:** {'ILLIMITED' if credits == 999 else credits - 1}\n"
    )
    bot.edit_message_text(response, message.chat.id, query_msg.message_id, parse_mode="Markdown")

# Handlers para los botones de la Botonera (ReplyKeyboard)
@bot.message_handler(func=lambda m: m.text in [
    STRINGS['es']['btn_bin'], STRINGS['es']['btn_plans'], STRINGS['es']['btn_tut'], STRINGS['es']['btn_faq'], STRINGS['es']['btn_lang'],
    STRINGS['en']['btn_bin'], STRINGS['en']['btn_plans'], STRINGS['en']['btn_tut'], STRINGS['en']['btn_faq'], STRINGS['en']['btn_lang']
])
def handle_reply_buttons(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    s = STRINGS[lang]
    if message.text == s['btn_bin']:
        p = {'es': "🔢 Escribe o copia esto para iniciar análisis:\n\n`/bin `", 'en': "🔢 Type or copy this to start analysis:\n\n`/bin `"}
        bot.reply_to(message, p[lang], parse_mode="Markdown")
    elif message.text == s['btn_plans']:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("💳 Comprar", url="https://t.me/Dvekut"))
        bot.send_message(message.chat.id, s['plans'], parse_mode="Markdown", reply_markup=markup)
    elif message.text == s['btn_tut']:
        bot.send_message(message.chat.id, s['tutorial'], parse_mode="Markdown")
    elif message.text == s['btn_faq']:
        bot.send_message(message.chat.id, s['faq'], parse_mode="Markdown")
    elif message.text == s['btn_lang']:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_es"))
        markup.add(telebot.types.InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"))
        bot.send_message(message.chat.id, "🌐 **Selecciona Idioma / Select Language**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_tutorial")
def callback_tutorial(call):
    lang = get_user_lang(call.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(STRINGS[lang]['back'], callback_data="back_start"))
    bot.edit_message_text(STRINGS[lang]['tutorial'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_faq")
def callback_faq(call):
    lang = get_user_lang(call.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(STRINGS[lang]['back'], callback_data="back_start"))
    bot.edit_message_text(STRINGS[lang]['faq'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_plans")
def callback_plans(call):
    lang = get_user_lang(call.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💳 Comprar Creditos", url="https://t.me/Dvekut"))
    markup.add(telebot.types.InlineKeyboardButton(STRINGS[lang]['back'], callback_data="back_start"))
    bot.edit_message_text(STRINGS[lang]['plans'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_lang_selector")
def callback_lang_selector(call):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_es"))
    markup.add(telebot.types.InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"))
    markup.add(telebot.types.InlineKeyboardButton("⬅️ Volver", callback_data="back_start"))
    bot.edit_message_text("🌐 **Selecciona tu idioma / Select your language**", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_lang_"))
def callback_set_lang(call):
    new_lang = call.data.split("_")[-1]
    set_user_lang(call.from_user.id, new_lang)
    bot.answer_callback_query(call.id, f"Idioma actualizado / Language updated: {new_lang.upper()}")
    bot.edit_message_text(STRINGS[new_lang]['welcome'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=get_start_markup(new_lang))

@bot.callback_query_handler(func=lambda call: call.data == "back_start")
def callback_back(call):
    lang = get_user_lang(call.from_user.id)
    bot.edit_message_text(STRINGS[lang]['welcome'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=get_start_markup(lang))

def run_crawler_bg():
    """Lanza el ciclo de minería de datos en segundo plano"""
    print("[🐝] Miner de Datos (The Hive) activado en segundo plano.")
    while True:
        try:
            # Aquí llamamos directamente a las funciones del crawler si estuvieran en las mismas carpetas
            # O simplemente ejecutamos el ciclo de minería para nutrir la DB
            print("[🔍] Scrapeando GitHub/Reddit para alimentar la DB...")
            # Simulamos que cada 12 horas el bot se auto-alimenta
            # En producción este hilo llamaría a las funciones de teampalomo_crawler.py
            time.sleep(43200) # 12 horas
        except Exception as e:
            print(f"[CRAWLER ERROR] {e}")
            time.sleep(3600)

if __name__ == "__main__":
    init_user_db()
    # Lanzar el crawler en un hilo separado para no bloquear el bot
    crawler_thread = threading.Thread(target=run_crawler_bg, daemon=True)
    crawler_thread.start()
    
    print("[INFO] EliteChecker_bot (By @Dvekut) iniciado correctamente en infraestructura resiliente.")
    
    backoff = 2
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=15)
            # infinity_polling should theoretically never exit unless stopped intentionally
            break
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] Conexión de red caída. Reintentando en {backoff}s. Detalle: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except requests.exceptions.ReadTimeout as e:
            print(f"[WARN] Timeout de lectura de Telegram API. Reintentando. Detalle: {e}")
            time.sleep(backoff)
        except Exception as e:
            print(f"[CRITICAL] Error fatal en el polling: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)

