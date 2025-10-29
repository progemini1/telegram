# -*- coding: utf-8 -*-

"""
Assalomu alaykum! Bu Mega Marafon botining 7-versiyasi ("PostgreSQL").

Bu versiya Railway.app (Server) va Neon.tech (Ma'lumotlar bazasi)
bilan ishlash uchun to'liq moslashtirilgan.

Mantiq v6 bilan bir xil, ammo ma'lumotlar bazasi SQLite'dan PostgreSQL'ga o'tkazilgan.
"""

import telebot
from telebot import types
import psycopg2  # SQLite o'rniga PostgreSQL kutubxonasi
import time
import threading
import os  # Serverdagi maxfiy linkni olish uchun

# --- Asosiy Sozlamalar ---
TOKEN = "7216166559:AAHJxqADiNAq5wO32OVrf4sJ0ukmQ53JUvA"

# --- Ma'lumotlar bazasi sozlamalari (NEON.TECH dan olinadi) ---
# DATABASE_URL Railway'dagi "Variables" bo'limidan olinadi.
DATABASE_URL = os.environ.get('DATABASE_URL')

# Agar DATABASE_URL topilmasa, bot ishga tushmaydi.
if not DATABASE_URL:
    print("XATOLIK: DATABASE_URL topilmadi. Railway'dagi 'Variables' bo'limini tekshiring.")
    # Ishga tushmasdan oldin to'xtatish
    # Bu qatorni vaqtincha kommentariyaga olsangiz, kodning qolgan qismini ko'ra olasiz,
    # lekin serverda bu tekshiruv juda muhim.
    # exit() 


# Kanallar ro'yxati va ularning tavsifi
CHANNEL_DESCRIPTIONS = {
    '@harvard_mit': '1-Kanal (Grantlar)',
    '@stanford777': '2-Kanal (Universitetlar)',
    '@TopUnilar': '3-Kanal (Maslahatlar)',
    '@TopGrantlar': '4-Kanal (Hujjatlar)'
}
CHANNELS = list(CHANNEL_DESCRIPTIONS.keys())

# Maxfiy kanal IDsi
PRIVATE_CHANNEL_ID = -1002832234  # Siz bergan ID

# Ball sozlamalari
POINTS_PER_REFERRAL = 5
REQUIRED_POINTS_FOR_REWARD = 50

# Botni yaratish
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# --- Ma'lumotlar bazasi (PostgreSQL) Funksiyalari ---

def get_db_connection():
    """Neon.tech bazasiga ulanishni yaratadi."""
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Ma'lumotlar bazasini va 'users' jadvalini yaratadi."""
    # SQL sintaksisi PostgreSQL uchun biroz o'zgartirildi (masalan, BOOLEAN)
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        referrer_id BIGINT,
        points INTEGER DEFAULT 0,
        has_subscribed BOOLEAN DEFAULT FALSE,
        reward_given BOOLEAN DEFAULT FALSE,
        referral_claimed BOOLEAN DEFAULT FALSE
    );
    '''
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        print("Ma'lumotlar bazasi jadvali (v7-PostgreSQL) tayyor.")
    except Exception as e:
        print(f"DB init xatosi: {e}")
    finally:
        if conn:
            conn.close()

def add_user(user_id, first_name, username, referrer_id=None):
    """
    Bazaga yangi foydalanuvchi qo'shadi (v6 mantiqi bilan - referal o'zgarmaydi).
    PostgreSQL uchun ON CONFLICT sintaksisi.
    """
    sql = '''
    INSERT INTO users (user_id, first_name, username, referrer_id, points, has_subscribed, reward_given, referral_claimed)
    VALUES (%s, %s, %s, %s, 0, FALSE, FALSE, FALSE)
    ON CONFLICT(user_id) DO UPDATE SET
        first_name = excluded.first_name,
        username = excluded.username
    '''
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, first_name, username, referrer_id))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"add_user xatosi: {e}")
    finally:
        if conn:
            conn.close()

def get_user_stats(user_id):
    """Foydalanuvchi statistikasini (ball, obuna) qaytaradi."""
    sql = "SELECT points, has_subscribed, reward_given FROM users WHERE user_id = %s"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"get_user_stats xatosi: {e}")
        return None
    finally:
        if conn:
            conn.close()

def set_subscribed_status(user_id, status):
    """Foydalanuvchining obuna holatini o'rnatadi."""
    sql = "UPDATE users SET has_subscribed = %s WHERE user_id = %s"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (status, user_id))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"set_subscribed_status xatosi: {e}")
    finally:
        if conn:
            conn.close()

def increment_points(user_id, points):
    """Foydalanuvchi ballarini oshiradi."""
    sql = "UPDATE users SET points = points + %s WHERE user_id = %s"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (points, user_id))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"increment_points xatosi: {e}")
    finally:
        if conn:
            conn.close()

def set_reward_given(user_id):
    """Foydalanuvchiga sovg'a berilganini belgilaydi."""
    sql = "UPDATE users SET reward_given = TRUE WHERE user_id = %s"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (user_id,))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"set_reward_given xatosi: {e}")
    finally:
        if conn:
            conn.close()

def claim_referral(user_id):
    """Referal ballari berilganini belgilaydi (referral_claimed = TRUE)."""
    sql = "UPDATE users SET referral_claimed = TRUE WHERE user_id = %s"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (user_id,))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"claim_referral xatosi: {e}")
    finally:
        if conn:
            conn.close()

def get_leaderboard():
    """TOP-10 foydalanuvchilar va ularning ballarini qaytaradi."""
    sql = "SELECT first_name, points FROM users ORDER BY points DESC LIMIT 10"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        leaders = cursor.fetchall()
        cursor.close()
        return leaders
    except Exception as e:
        print(f"get_leaderboard xatosi: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_rank(user_id):
    """Foydalanuvchining umumiy reytingdagi o'rnini qaytaradi."""
    sql = "SELECT user_id, points FROM users ORDER BY points DESC"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        all_users = cursor.fetchall()
        cursor.close()
        rank = 0
        for i, (uid, points) in enumerate(all_users):
            if uid == user_id:
                rank = i + 1
                break
        return rank, len(all_users)
    except Exception as e:
        print(f"get_user_rank xatosi: {e}")
        return 0, 0
    finally:
        if conn:
            conn.close()

# --- Yordamchi funksiyalar (Motivatsiya va UX - O'ZGARTIRILMAGAN) ---
# (Bu yerdagi barcha mantiq avvalgi v6 bilan bir xil)

def check_subscription(user_id):
    """
    Foydalanuvchining kanallarga a'zoligini tekshiradi.
    QAYTARADI: Ro'yxat. A'zo BO'LMAGAN kanallar ro'yxatini qaytaradi.
    """
    missing_channels = []
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                missing_channels.append(channel)
        except Exception as e:
            if 'user not found' in str(e):
                missing_channels.append(channel) 
            else:
                print(f"Obunani tekshirish xatosi ({user_id} {channel}): {e}")
                missing_channels.append(channel) 
    return missing_channels

def generate_adaptive_keyboard(missing_list):
    """
    Faqat obuna bo'linmagan kanallar ro'yxati (Adaptiv UX)
    va tekshirish tugmasini yaratadi.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_username in missing_list:
        description = CHANNEL_DESCRIPTIONS.get(channel_username, channel_username)
        url = f"https://t.me/{channel_username[1:]}"
        keyboard.add(types.InlineKeyboardButton(f"▶️ {description}", url=url))
    
    check_button_text = "🏁 Obunani Tekshirish"
    if len(missing_list) != len(CHANNELS):
        check_button_text = "🏁 Qayta Tekshirish"
        
    keyboard.add(types.InlineKeyboardButton(check_button_text, callback_data="check_subscription"))
    return keyboard

def generate_main_menu():
    """Asosiy menyu tugmalarini yaratadi (Obunadan so'ng)."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add("🚀 Do'stlarni taklif qilish", "📈 Mening statistikam")
    keyboard.add("🏆 Marafon Jadvali")
    return keyboard

def send_main_menu(user_id):
    """Foydalanuvchiga asosiy menyuni va referal xabarini yuboradi. (Kuchli Motivatsiya)"""
    try:
        stats = get_user_stats(user_id)
        if not stats:
            print(f"Xato: send_main_menu da {user_id} uchun statistika topilmadi.")
            return

        points = stats[0]
        needed_points = REQUIRED_POINTS_FOR_REWARD - points
        needed_friends = (needed_points + POINTS_PER_REFERRAL - 1) // POINTS_PER_REFERRAL 

        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"

        # Asosiy xabar - Marketing
        text = "🏁 <b>START CHIZIG'IDASIZ!</b>\n\n"
        text += "Tabriklaymiz, siz marafonning to'laqonli ishtirokchisisiz. Endi asosiy kurash boshlanadi!\n\n"
        text += "🎯 <b>Sizning birinchi vazifangiz:</b> <b>10 ta do'stingizni</b> (<b>50 ball</b>) taklif qilish orqali birinchi EKSKLYUZIV sovg'aga — maxfiy kanalga yo'llanma olish.\n\n"
        
        if needed_points > 0:
            text += f"📈 <b>Motivatsiyani yo'qotmang!</b> Sizga birinchi marragacha yana <b>{needed_points} ball</b> ({needed_friends} ta do'st) qoldi.\n\n"
        else:
            text += "✅ <b>Siz birinchi vazifani bajardingiz!</b> Sovg'ani olmadingizmi? /status ni bosing.\n\n"

        text += "<b>Sizning shaxsiy taklif linkingiz:</b>\n"
        text += f"<code>{referral_link}</code>\n\n"
        text += "👇 Ushbu linkni do'stlaringizga yuboring yoki quyidagi tugmani bosing."
        
        try:
            bot_name = bot.get_me().first_name
        except Exception:
            bot_name = "Mega Marafon"

        # "Viral" bo'lishi uchun ulashish matni (sizning talabingiz bo'yicha)
        share_text = f"Do'stlar, keling! Men {bot_name}da qatnashyapman, bu haqiqatdan ham zo'r bo'lyapti! 🔥 Bu yerda nafaqat bilim va ko'nikmalar, balki qimmatbaho sovg'alar ham bor ekan! 🏆 Siz ham qo'shiling, marafondan qolib ketmang!"
        share_url = f"https://t.me/share/url?url={referral_link}&text={share_text}"
        
        inline_keyboard = types.InlineKeyboardMarkup()
        inline_keyboard.add(types.InlineKeyboardButton("🔗 Do'stlarga Ulashish", url=share_url))

        bot.send_message(user_id, text, reply_markup=generate_main_menu())
        bot.send_message(user_id, "<i>Pastdagi 'Do'stlarga Ulashish' tugmasi orqali marafonga chaqirish yanada osonroq:</i>", reply_markup=inline_keyboard)

    except Exception as e:
        print(f"send_main_menu xatosi: {e}")

def send_reward(user_id):
    """Foydalanuvchiga bir martalik link va KUCHLI motivatsion xabar yuboradi."""
    try:
        expire_date = int(time.time()) + 3600  # 1 soat
        link = bot.create_chat_invite_link(PRIVATE_CHANNEL_ID, member_limit=1, expire_date=expire_date)
        
        # 1-XABAR: Sovg'a
        reward_text = f"💎 <b>BIRINCHI MARRA SIZNIKI! TABRIKLAYMIZ!</b> 💎\n\n"
        reward_text += "Siz <b>10 ta do'stingizni</b> muvaffaqiyatli taklif qildingiz va <b>EKSKLYUZIV</b> kanalimizga yo'llanmani qo'lga kiritdingiz!\n\n"
        reward_text += "❗️ Bu sizning shaxsiy, <b>BIR MARTALIK</b> taklif linkingiz. U faqat 1 soat amal qiladi:\n\n"
        reward_text += f"➡️ <b>{link.invite_link}</b> ⬅️\n\n"
        reward_text += "<i>Tezroq kanalga qo'shilib oling va kurashni kuzatib boring!</i>"
        
        bot.send_message(user_id, reward_text)
        
        set_reward_given(user_id)
        
        # 2-XABAR: Motivatsiya (2 soniyadan keyin)
        time.sleep(2)
        motivation_text = "<b>To'xtamang! Bu faqat boshlanishi!</b> 🚀\n\n"
        motivation_text += "Siz Eksklyuziv kanalga yo'llanmani qo'lga kiritdingiz, ammo <b>ASOSIY SOVRINLAR</b> — 1-o'rin uchun kurash hali oldinda!\n\n"
        motivation_text += "🏆 <b>Yodingizda tuting:</b> Faqat eng kuchli TOP-3 ishtirokchilar marafon yakunida <b>QIMMATBAHO SOVG'ALAR</b> bilan taqdirlanadi.\n\n"
        motivation_text += f"Sizda allaqachon <b>{REQUIRED_POINTS_FOR_REWARD} ball</b> bor, raqobatchilaringizga imkoniyat qoldirmang. <b>Yangi rekordlar sari olg'a!</b>"
        
        bot.send_message(user_id, motivation_text)

    except Exception as e:
        print(f"Sovg'a yuborish xatosi: {e}")
        bot.send_message(user_id, "❗️ Sovg'a linkini yaratishda xatolik yuz berdi. Iltimos, administrator bilan bog'laning.")

# --- Botning Asosiy Handler'lari ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Botga /start buyrug'i kelganda ishlaydi."""
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        print(f"/start bosildi: {user_id} ({first_name})")

        referrer_id = None
        if message.text and len(message.text.split()) > 1:
            try:
                potential_id = int(message.text.split()[1])
                if potential_id != user_id: # O'ziga o'zi referal bo'lolmaydi
                    referrer_id = potential_id
            except (ValueError, IndexError):
                pass
        
        # Bu funksiya referalni faqat bir marta, ISHONCHLI yozadi (v7 Mantiq)
        add_user(user_id, first_name, username, referrer_id)
        
        # Kuchaytirilgan marketing matni
        welcome_text = f"🏆 <b>Xush kelibsiz, {first_name}!</b>\n\n"
        welcome_text += "Siz shunchaki botga emas, <b>YILNING ENG KATTA MEGA MARAFONIGA</b> muvaffaqiyatli qo'shildingiz!\n\n"
        welcome_text += "🔥 Bu imkoniyat faqat <b>yilda bir marta</b> beriladi! Sizni nafaqat TOP Universitetlar va Grantlar olamiga olib kiruvchi EKSKLYUZIV bilimlar, balki marafon g'oliblari uchun <b>MO'LJALLANGAN QIMMATBAHO SOVG'ALAR</b> kutmoqda!\n\n"
        welcome_text += "🏁 <b>MARAFON BOSHLANDI!</b> G'oliblar qatorida bo'lish uchun birinchi shart: 4 ta rasmiy kanalimizga obuna bo'ling va \"🏁 Obunani Tekshirish\" tugmasini bosing:"
        
        # Boshlang'ich tugmalar (barcha 4 kanal)
        initial_keyboard = generate_adaptive_keyboard(CHANNELS)
        bot.send_message(user_id, welcome_text, reply_markup=initial_keyboard)

    except Exception as e:
        print(f"/start xatosi: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def handle_check_subscription(call):
    """'🏁 Obunani Tekshirish' tugmasi bosilganda ishlaydi. (Adaptiv Mantiq)"""
    user_id = call.from_user.id
    try:
        # "Aqlli" tekshiruv: faqat obuna bo'linmagan kanallarni qaytaradi
        missing = check_subscription(user_id) 
        
        if len(missing) == 0:
            # --- HAMMASIGA OBUNA BO'LINGAN (MUVAFFAQIYAT) ---
            bot.answer_callback_query(call.id, "✅ Ajoyib! Siz marafonga qo'shildingiz!")
            try:
                # Tugmalarni o'chirish
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                print(f"Xabarni o'chirish xatosi: {e}")
            
            set_subscribed_status(user_id, 1)
            
            # --- REFERAL BALLARINI BIR MARTA BERISH MANTIG'I (v7) ---
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT referrer_id, referral_claimed FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                referrer_id = result[0] if result else None
                referral_claimed = result[1] if result else False
                
                if referrer_id and not referral_claimed:
                    # 1. Ball qo'shamiz
                    cursor.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (POINTS_PER_REFERRAL, referrer_id))
                    
                    # 2. "Hisoblandi" deb belgilaymiz (qayta ball berilmaydi)
                    cursor.execute("UPDATE users SET referral_claimed = TRUE WHERE user_id = %s", (user_id,))
                    
                    conn.commit()
                    print(f"Ball berildi: {referrer_id} ga {user_id} uchun {POINTS_PER_REFERRAL} ball qo'shildi.")
                    
                    # Referalga xabar berish
                    try:
                        cursor.execute("SELECT points, reward_given FROM users WHERE user_id = %s", (referrer_id,))
                        referrer_stats = cursor.fetchone()
                        
                        if referrer_stats:
                            new_points = referrer_stats[0]
                            reward_given = referrer_stats[1]
                            bot.send_message(referrer_id, f"🚀 <b>Yaxshi ish!</b> Siz <b>{call.from_user.first_name}</b>ni jamoangizga qo'shdingiz va <b>{POINTS_PER_REFERRAL} ball</b> oldingiz!\n\n"
                                                        f"Sizning jami ballingiz: <b>{new_points}</b>. Maqsad sari olg'a!")
                            
                            # Agar shu ball bilan 50 ga yetgan bo'lsa va sovg'a olmagan bo'lsa
                            if new_points >= REQUIRED_POINTS_FOR_REWARD and not reward_given:
                                # send_reward() o'z ulanishini o'zi ochadi
                                send_reward(referrer_id)
                    except Exception as e:
                        print(f"Referalga xabar yuborish xatosi: {e}")
                
                cursor.close()
            except Exception as e:
                print(f"Ball berish mantiqi xatosi: {e}")
            finally:
                if conn:
                    conn.close()

            # Asosiy menyuni yuborish
            send_main_menu(user_id)
            
        else:
            # --- HALI OBUNA BO'LINMAGAN KANALLAR BOR (ADAPTIV UX) ---
            
            # 1. Ogohlantirish berish
            alert_text = f"⚠️ Iltimos, quyidagi {len(missing)} ta kanalga obuna bo'ling:"
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
            
            # 2. Tugmalarni FAQA_T obuna bo'linmagan kanallar bilan yangilash
            new_keyboard = generate_adaptive_keyboard(missing)
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=new_keyboard
            )
            set_subscribed_status(user_id, 0) 
            
    except Exception as e:
        bot.answer_callback_query(call.id, "Xatolik yuz berdi. Qayta urinib ko'ring.")
        print(f"check_subscription callback xatosi: {e}")

def check_subscription_and_proceed(message, function_to_run):
    """
    Bu funksiya avval obunani tekshiradi (kanaldan chiqib ketmaganligini).
    """
    user_id = message.from_user.id
    try:
        missing = check_subscription(user_id) 
        
        if len(missing) == 0:
            set_subscribed_status(user_id, 1) 
            function_to_run(message) # Asosiy funksiyani (statistika/liderlar) ishga tushirish
        else:
            # Foydalanuvchi kanaldan chiqib ketgan
            set_subscribed_status(user_id, 0)
            bot.send_message(user_id, "❗️ <b>Marafondan chetlatildingiz!</b>\n\nBotdan foydalanish uchun barcha 4 ta kanalga obuna bo'lishingiz shart.", reply_markup=types.ReplyKeyboardRemove())
            
            # Unga faqat obuna bo'linmagan kanallarni ko'rsatish
            missing_keyboard = generate_adaptive_keyboard(missing)
            bot.send_message(user_id, "Iltimos, kanallarga qayta obuna bo'ling va \"🏁 Obunani Tekshirish\" tugmasini bosing:", reply_markup=missing_keyboard)
    
    except Exception as e:
        print(f"check_subscription_and_proceed xatosi: {e}")

# --- Statistikaga oid tugmalar ---

@bot.message_handler(commands=['status'])
def handle_status_command(message):
    """/status buyrug'ini ushlaydi va statistika funksiyasiga yo'naltiradi."""
    check_subscription_and_proceed(message, handle_show_stats)

@bot.message_handler(func=lambda message: message.text == "📈 Mening statistikam")
def handle_stats_button(message):
    """'Mening statistikam' tugmasini ushlaydi."""
    check_subscription_and_proceed(message, handle_show_stats)

def handle_show_stats(message):
    """Foydalanuvchiga uning statistikasini ko'rsatadi. (Kuchli Motivatsiya)"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    try:
        stats = get_user_stats(user_id)
        if not stats:
            bot.send_message(user_id, "Sizning statistikangiz topilmadi. /start ni bosing.")
            return
            
        points = stats[0]
        reward_given = stats[2]
        
        friends_count = points // POINTS_PER_REFERRAL
        needed_points = REQUIRED_POINTS_FOR_REWARD - points
        
        text = f"📈 <b>Sizning shaxsiy statistikangiz, {first_name}:</b>\n\n"
        text += f"🔹 <b>Jami ball:</b> {points} ball\n"
        text += f"🔹 <b>Taklif qilingan do'stlar:</b> {friends_count} ta\n\n"
        
        if not reward_given:
            if needed_points > 0:
                needed_friends = (needed_points + POINTS_PER_REFERRAL - 1) // POINTS_PER_REFERRAL
                text += f"🎯 <b>Eksklyuziv kanal uchun:</b> yana <b>{needed_points} ball</b> ({needed_friends} ta do'st) kerak.\n\n"
                text += f"🚀 <b>Harakat qiling, {first_name}!</b> Eksklyuziv kanal eshiklari ochilishiga juda oz qoldi!"
            else:
                text += "✅ <b>Tabriklaymiz!</b> Siz eksklyuziv kanal uchun yetarli ball to'pladingiz!\n"
                text += "Sovg'angiz tez orada avtomatik tarzda yuboriladi (agar yuborilmagan bo'lsa)."
        else:
            text += "✅ <b>Siz eksklyuziv kanalga yo'llanmani qo'lga kiritgansiz!</b>\n\n"
            text += "🏆 <b>YUQORI TEMPNI SAQLANG!</b> Siz birinchi marraga yetdingiz, ammo asosiy marafon (TOP-3) endi boshlandi. Raqobatchilaringiz ortda qolmasin!"

        bot.send_message(user_id, text)

    except Exception as e:
        print(f"handle_show_stats xatosi: {e}")

@bot.message_handler(func=lambda message: message.text == "🏆 Marafon Jadvali")
def handle_leaderboard_button(message):
    """'Marafon Jadvali' tugmasini ushlaydi."""
    check_subscription_and_proceed(message, handle_show_leaderboard)

def handle_show_leaderboard(message):
    """Foydalanuvchiga liderlar ro'yxatini ko'rsatadi."""
    user_id = message.from_user.id
    try:
        leaders = get_leaderboard()
        rank, total_users = get_user_rank(user_id)
        
        text = "📊 <b>MEGA MARAFON JADVALI (TOP-10)</b> 🏆\n\n"
        
        if not leaders:
            text += "Hozircha liderlar yo'q. Birinchi bo'ling!\n"
        else:
            for i, (first_name, points) in enumerate(leaders):
                emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                safe_name = telebot.util.escape(first_name)
                text += f"{emoji[i]} <b>{safe_name}</b> - {points} ball\n"
                
        text += "\n" + ("➖" * 15) + "\n\n"
        
        if rank > 0:
            if rank <= 10:
                text += f"🎯 <b>Sizning o'rningiz:</b>\nSiz TOP-10 g'oliblar qatoridasiz (<b>{rank}-o'rin</b>)! ✨ Bu ajoyib natija! Shu tempni saqlang!\n\n"
            else:
                text += f"🎯 <b>Sizning o'rningiz:</b>\nSiz hozirda <b>{total_users}</b> ishtirokchi orasida <b>{rank}-o'rindasiz</b>. Kuchliroq harakat qilib, TOP-10 ga kiring!\n\n"
        else:
            text += "Siz hali reytingda yo'qsiz. Do'stlarni taklif qilishni boshlang!\n\n"

        text += "<i><b>Unutmang: har bir yangi do'st sizni 1-o'ringa yaqinlashtiradi!</b></i>"
        
        bot.send_message(user_id, text)

    except Exception as e:
        print(f"handle_show_leaderboard xatosi: {e}")

@bot.message_handler(func=lambda message: message.text == "🚀 Do'stlarni taklif qilish")
def handle_invite_button(message):
    """'Do'stlarni taklif qilish' tugmasini ushlaydi va linkni qayta yuboradi."""
    check_subscription_and_proceed(message, send_referral_link_again)

def send_referral_link_again(message):
    """Foydalanuvchiga uning referal linkini va ulashish tugmasini qayta yuboradi."""
    user_id = message.from_user.id
    try:
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"

        text = "Sizning shaxsiy referal linkingiz:\n\n"
        text += f"<code>{referral_link}</code>\n\n"
        text += "👇 Ushbu linkni nusxalub oling yoki quyidagi tugma orqali do'stlaringizga yuboring."

        try:
            bot_name = bot.get_me().first_name
        except Exception:
            bot_name = "Mega Marafon"
            
        share_text = f"Do'stlar, keling! Men {bot_name}da qatnashyapman, bu haqiqatdan ham zo'r bo'lyapti! 🔥 Bu yerda nafaqat bilim va ko'nikmalar, balki qimmatbaho sovg'alar ham bor ekan! 🏆 Siz ham qo'shiling, marafondan qolib ketmang!"
        share_url = f"https://t.me/share/url?url={referral_link}&text={share_text}"
        
        inline_keyboard = types.InlineKeyboardMarkup()
        inline_keyboard.add(types.InlineKeyboardButton("🔗 Do'stlarga Ulashish", url=share_url))
        
        bot.send_message(user_id, text, reply_markup=inline_keyboard)
    
    except Exception as e:
        print(f"send_referral_link_again xatosi: {e}")

@bot.message_handler(func=lambda message: True)
def handle_unknown_text(message):
    """Har qanday tanilmagan matnga javob beradi. (Yaxshilangan UX)"""
    user_id = message.from_user.id
    try:
        stats = get_user_stats(user_id)
        if stats and stats[1]: # (has_subscribed == 1)
            bot.send_message(user_id, "Iltimos, tushunarli buyruq berish uchun pastdagi <b>tugmalardan</b> foydalaning 👇", reply_markup=generate_main_menu())
        else:
            bot.send_message(user_id, "Botni ishlatish uchun /start buyrug'ini bosing va kanallarga obuna bo'ling.")
    except Exception as e:
        print(f"handle_unknown_text xatosi: {e}")

# --- Botni ishga tushirish (Xatolikka chidamli) ---
def start_bot():
    """Botni doimiy (while True) rejimda ishga tushiradi."""
    print("Ma'lumotlar bazasi (v7-PostgreSQL) tayyorlanmoqda...")
    init_db()
    print("Bot ishga tushmoqda... (v7 - Yakuniy Optimizatsiya)")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=25)
        except Exception as e:
            print(f"KRITIK XATO: Bot to'xtadi: {e}")
            print("Server 5 soniyadan so'ng qayta ishga tushmoqda...")
            time.sleep(5)

if __name__ == '__main__':
    start_bot()
