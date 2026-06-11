import logging
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

# --- CONFIG LOGGING ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DANH SÁCH GAME & LINK API (ĐÃ BỎ LUCK8 VÀ SON789 MD5) ---
GAME_CONFIG = {
    "SUNWIN": {"name": "SUNWIN", "url": "https://trails-wish-motel-legacy.trycloudflare.com/api/tx"},
    "OGK_FAN": {"name": "OGK FAN", "url": "https://guidance-discrete-dive-navigate.trycloudflare.com/api/txmd5/latest"},
    "XOCDIA88": {"name": "XOCDIA88", "url": "https://pollution-seconds-sail-strikes.trycloudflare.com/api/taixiu"},
    "HITCLUB_MD5": {"name": "HITCLUB MD5", "url": "https://subdivision-term-came-attempting.trycloudflare.com/api/txmd5"},
    "HITCLUB": {"name": "HITCLUB", "url": "https://subdivision-term-came-attempting.trycloudflare.com/api/tx"},
    "LC79_MD5": {"name": "LC79 MD5", "url": "https://thread-broke-artwork-compound.trycloudflare.com/api/txmd5"},
    "LC79": {"name": "LC79", "url": "https://thread-broke-artwork-compound.trycloudflare.com/api/tx"},
    "BETVIP_MD5": {"name": "BETVIP MD5", "url": "https://stored-could-elder-mini.trycloudflare.com/api/txmd5"},
    "BETVIP": {"name": "BETVIP", "url": "https://stored-could-elder-mini.trycloudflare.com/api/tx"},
    "789CLUB": {"name": "789CLUB", "url": "https://packet-veterinary-organ-ministers.trycloudflare.com/api/tx"},
    "B52_MD5": {"name": "B52 MD5", "url": "https://years-expiration-autos-concert.trycloudflare.com/txmd5"},
    "B52": {"name": "B52", "url": "https://years-expiration-autos-concert.trycloudflare.com/taixiu"},
    "IWIN_MD5": {"name": "IWIN MD5", "url": "https://seek-vessels-peripherals-song.trycloudflare.com/api/txmd5"},
    "IWIN": {"name": "IWIN", "url": "https://seek-vessels-peripherals-song.trycloudflare.com/api/tx"},
    "MAX789_MD5": {"name": "MAX789 MD5", "url": "https://expected-paying-pins-childhood.trycloudflare.com/api/txmd5"},
    "MAX789": {"name": "MAX789", "url": "https://expected-paying-pins-childhood.trycloudflare.com/api/tx"},
    "SON789": {"name": "SON789", "url": "https://howto-out-excluding-tan.trycloudflare.com/api/tx"},
    "SUMVIN_MD5": {"name": "SUMVIN MD5", "url": "https://stories-meetings-injection-headlines.trycloudflare.com/api/md5"},
    "68GB_MD5": {"name": "68GB MD5", "url": "https://chuck-ent-nicole-leadership.trycloudflare.com/api/68/md5"},
    "68GB": {"name": "68GB", "url": "https://financing-patio-beast-invention.trycloudflare.com/api/68/thuong"},
    "SUN789_MD5": {"name": "SUN789 MD5", "url": "https://speeds-built-attendance-dedicated.trycloudflare.com/api/txmd5"},
    "SUN789": {"name": "SUN789", "url": "https://speeds-built-attendance-dedicated.trycloudflare.com/api/tx"},
    "HOT789_MD5": {"name": "HOT789 MD5", "url": "https://improve-museum-der-levy.trycloudflare.com/api/txmd5"},
    "HOT789": {"name": "HOT789", "url": "https://improve-museum-der-levy.trycloudflare.com/api/tx"},
    "TA28_MD5": {"name": "TA28 MD5", "url": "https://conversation-selling-slowly-bride.trycloudflare.com/api/txmd5"},
    "TA28": {"name": "TA28", "url": "https://conversation-selling-slowly-bride.trycloudflare.com/api/tx"},
}

def build_main_menu():
    keyboard = []
    keys = list(GAME_CONFIG.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(GAME_CONFIG[keys[i]]["name"], callback_data=f"g_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(GAME_CONFIG[keys[i+1]]["name"], callback_data=f"g_{keys[i+1]}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

user_stats = {} 
active_tasks = {}

def get_or_create_stats(user_id, game_id):
    if user_id not in user_stats:
        user_stats[user_id] = {}
    if game_id not in user_stats[user_id]:
        user_stats[user_id][game_id] = {
            "win": 0, 
            "lose": 0, 
            "last_predicted_session": 0, 
            "last_prediction": None,
            "processed_sessions": set()
        }
    return user_stats[user_id][game_id]


# === NÂNG CẤP BỘ PHÂN TÍCH THẾ CẦU TOÀN DIỆN (TUYỆT ĐỐI KHÔNG RANDOM) ===
class PremiumAnalyzer:
    def __init__(self, history):
        self.history = history  # Mảng chứa chuỗi xuôi dòng thời gian (0: Xiu, 1: Tai)
        self.length = len(history)

    def analyze(self):
        if self.length < 6:
            return "Tai" if (self.history[-1] if self.length > 0 else 1) == 0 else "Xiu"

        # Đọc độ dài chuỗi đuôi gần nhất
        last_1 = self.history[-1]
        last_2 = self.history[-2:]
        last_3 = self.history[-3:]
        last_4 = self.history[-4:]
        last_5 = self.history[-5:]
        last_6 = self.history[-6:]

        # 1. KIỂM TRA CẦU BỆT VÀ CẦU GÃY
        streak = 1
        for i in range(self.length - 2, -1, -1):
            if self.history[i] == last_1:
                streak += 1
            else:
                break
        
        if streak >= 6:  # Cầu bệt quá dài -> Dự đoán CẦU GÃY (Bẻ cầu)
            return "Xiu" if last_1 == 1 else "Tai"
        if streak >= 3:  # Cầu đang bệt từ 3 đến 5 tay -> Dự đoán TIẾP TỤC ĐU BỆT
            return "Tai" if last_1 == 1 else "Xiu"

        # 2. KIỂM TRA CẦU XEN KẼ / ZIGZAG (1-1)
        if last_4 == [1, 0, 1, 0]: return "Tai"
        if last_4 == [0, 1, 0, 1]: return "Xiu"
        if last_5 == [1, 0, 1, 0, 1]: return "Xiu"
        if last_5 == [0, 1, 0, 1, 0]: return "Tai"

        # 3. KIỂM TRA CẦU ĐÔI HÌNH HỌC (2-2)
        if last_4 == [1, 1, 0, 0]: return "Tai"
        if last_4 == [0, 0, 1, 1]: return "Xiu"
        if last_5 == [1, 1, 0, 0, 1]: return "Tai"
        if last_5 == [0, 0, 1, 1, 0]: return "Xiu"

        # 4. KIỂM TRA CẦU BA HÌNH HỌC (3-3)
        if last_6 == [1, 1, 1, 0, 0, 0]: return "Tai"
        if last_6 == [0, 0, 0, 1, 1, 1]: return "Xiu"

        # 5. KIỂM TRA CẦU TỔ HỢP LÙI TIẾN (3-2-1, 1-2-3)
        if last_6 == [1, 1, 1, 0, 0, 1]: return "Xiu" # Gãy nhịp 3-2-1 sang cầu đảo
        if last_5 == [1, 1, 1, 0, 0]: return "Tai"    # Đúng khuôn 3-2 -> Ra 1
        if last_5 == [0, 0, 0, 1, 1]: return "Xiu"    # Đúng khuôn 3-2 -> Ra 1
        if last_6 == [0, 1, 1, 0, 0, 0]: return "Tai"  # Cầu tiến 1-2-3

        # 6. KIỂM TRA CẦU ĐẶC BIỆT (2-2-1-1, 3-1-3, 3-4-1)
        if last_6 == [1, 1, 0, 0, 1, 0]: return "Tai"  # Hết khuôn 2-2-1-1 quay lại nhịp đối
        if last_4 == [1, 1, 0, 1]: return "Xiu"        # Cầu cấu trúc 2-1-1
        if last_4 == [0, 0, 1, 0]: return "Tai"        # Cầu cấu trúc 2-1-1

        # 7. LOGIC MẶC ĐỊNH NẾU KHÔNG KHỚP KHUÔN (BẮT ĐẢO CẦU CŨ CẬP NHẬT)
        return "Tai" if last_1 == 0 else "Xiu"


async def fetch_api_data_isolated(url):
    try:
        timeout = aiohttp.ClientTimeout(total=3.5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    json_data = await response.json()
                    
                    if isinstance(json_data, list) and len(json_data) > 0:
                        data_list = json_data
                        latest = json_data[0]
                    elif isinstance(json_data, dict):
                        data_list = json_data.get("data") or json_data.get("list") or json_data.get("results") or [json_data]
                        latest = data_list[0] if isinstance(data_list, list) and len(data_list) > 0 else json_data
                    else:
                        return None
                    
                    session_id = None
                    for key in ["phien", "session", "session_id", "game_session", "id", "code"]:
                        val = latest.get(key)
                        if val is not None and str(val).isdigit():
                            val_int = int(val)
                            if val_int > 10000:
                                session_id = val_int
                                break
                    
                    if session_id is None:
                        session_id = latest.get("phien") or latest.get("session") or 100000
                        try:
                            session_id = int(session_id)
                        except ValueError:
                            session_id = 100000
                    
                    history_raw = []
                    if isinstance(data_list, list):
                        for item in data_list[:15][::-1]:
                            kq_str = str(item.get("ketqua") or item.get("result") or item.get("kq") or "").lower()
                            kq_num = item.get("tongdiem") or item.get("total") or item.get("score") or item.get("point") or 0
                            
                            is_tai = False
                            if "tai" in kq_str or "t" in kq_str or "chẵn" in kq_str:
                                is_tai = True
                            elif "xiu" in kq_str or "x" in kq_str or "lẻ" in kq_str:
                                is_tai = False
                            elif isinstance(kq_num, (int, float)) and kq_num > 0:
                                is_tai = (kq_num > 10)
                            elif item.get("tai") is not None:
                                is_tai = (int(item.get("tai")) == 1)
                                
                            history_raw.append(1 if is_tai else 0)
                    
                    if not history_raw:
                        history_raw = [1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1]
                        
                    return int(session_id), history_raw
    except Exception:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        del active_tasks[user_id]
        
    await update.message.reply_text(
        "Chào Mừng Bạn Đến Với Tool Phân Tích!!\n\nChon nha cai ben duoi:", 
        reply_markup=build_main_menu()
    )

async def render_game_screen(query, user_id, game_id, current_live_session, history_data):
    game_info = GAME_CONFIG[game_id]
    stats = get_or_create_stats(user_id, game_id)
    next_session = current_live_session + 1
    
    if stats["last_prediction"] is not None and stats["last_predicted_session"] == current_live_session:
        if current_live_session not in stats["processed_sessions"]:
            actual_result = "Tai" if history_data[-1] == 1 else "Xiu"
            if stats["last_prediction"] == actual_result:
                stats["win"] += 1
            else:
                stats["lose"] += 1
            stats["processed_sessions"].add(current_live_session)

    # Khởi chạy bộ thuật toán phân tích đa tầng thế cầu mới nâng cấp
    pred = PremiumAnalyzer(history_data).analyze()
    stats["last_predicted_session"] = next_session
    stats["last_prediction"] = pred

    text = (
        f"Nha Cai: {game_info['name']}\n"
        f"==========\n"
        f"Phien: {next_session}\n"
        f"Du Doan: {pred}\n"
        f"==========\n\n"
        f"Tong Thang: {stats['win']}\n"
        f"Tong Thua: {stats['lose']}"
    )
    
    back_keys = InlineKeyboardMarkup([[
        InlineKeyboardButton("Lam Moi", callback_data=f"g_{game_id}"),
        InlineKeyboardButton("Quay Lai", callback_data="back")
    ]])
    
    try:
        await query.edit_message_text(text=text, reply_markup=back_keys)
    except BadRequest:
        pass

async def auto_refresh_loop(query, user_id, game_id, last_seen_session):
    game_info = GAME_CONFIG[game_id]
    while True:
        try:
            await asyncio.sleep(3)
            api_result = await fetch_api_data_isolated(game_info["url"])
            
            if api_result:
                current_live_session, history_data = api_result
                if current_live_session > last_seen_session:
                    last_seen_session = current_live_session
                    await render_game_screen(query, user_id, game_id, current_live_session, history_data)
            else:
                await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2)

async def handle_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("g_", "")
    user_id = update.effective_user.id
    
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        await asyncio.sleep(0.1)

    api_result = await fetch_api_data_isolated(GAME_CONFIG[game_id]["url"])
    if api_result:
        current_live_session, history_data = api_result
    else:
        current_live_session, history_data = 100000, [1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1]

    await render_game_screen(query, user_id, game_id, current_live_session, history_data)
    
    task = asyncio.create_task(auto_refresh_loop(query, user_id, game_id, current_live_session))
    active_tasks[user_id] = task

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        del active_tasks[user_id]
        
    await query.edit_message_text(
        "Chào Mừng Bạn Đến Với Tool Phân Tích!!\n\nChon nha cai ben duoi:", 
        reply_markup=build_main_menu()
    )

def main():
    TOKEN = "8928203653:AAH-ZeXKDSVRf89fkP0RQet7kuc2cCDj3sE"
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_game, pattern="^g_"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    
    print("Bot da nang cap nang luc quet the cau phuc tap cao. Dang chay...")
    app.run_polling()

if __name__ == "__main__":
    main()
