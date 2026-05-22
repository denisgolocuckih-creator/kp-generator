import os
import json
import tempfile
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pdfkit

load_dotenv()

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "8692980333:AAE-XMAjy145lc8Gidtgn5lEM8Fy"  # Замените на реальный токен

# ========== ИИ ==========
def get_llm():
    load_dotenv()
    return ChatOpenAI(
        model="deepseek/deepseek-chat",
        temperature=0.1,
        openai_api_key=os.getenv("VSEGPT_API_KEY"),
        openai_api_base="https://api.vsegpt.ru/v1"
    )

def load_price_list():
    with open("data/prices.txt", "r", encoding="utf-8") as f:
        return f.read()

def calculate_kp(user_input):
    price_list = load_price_list()
    prompt = f"""
Ты — ИИ-калькулятор строительной компании. Рассчитай КП СТРОГО по базе знаний.

=== БАЗА ЗНАНИЙ ===
{price_list}
=== КОНЕЦ БАЗЫ ===

ПРАВИЛА:
1. Выдели: тип объекта, площадь, класс, особые условия.
2. Базовая стоимость = Площадь × Ставка.
3. Коэффициенты применяй ПОСЛЕДОВАТЕЛЬНО.
4. Скидки применяй ПОСЛЕДОВАТЕЛЬНО.
5. Срок = Площадь / 50.

ФОРМАТ ОТВЕТА — ТОЛЬКО JSON:
{{
  "тип_объекта": "...",
  "площадь_квм": ...,
  "базовая_ставка_за_квм": ...,
  "базовая_стоимость": ...,
  "коэффициенты": [{{"название": "...", "процент": ..., "сумма": ...}}],
  "стоимость_после_коэффициентов": ...,
  "скидки": [{{"название": "...", "процент": ..., "сумма": ...}}],
  "итоговая_стоимость": ...,
  "срок_месяцев": ...,
  "комментарий": "..."
}}
"""
    result = get_llm().invoke(f"{prompt}\n\nЗАПРОС: {user_input}\n\nВерни ТОЛЬКО JSON:")
    return result.content

def generate_pdf(data):
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    html = f"""
    <html><head><meta charset="utf-8"><style>
        body {{ font-family: Arial; margin: 40px; }}
        h1 {{ text-align: center; color: #2c3e50; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f5f5f5; }}
    </style></head><body>
        <h1>КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ</h1>
        <p>Дата: {datetime.now().strftime('%d.%m.%Y')}</p>
        <h2>Объект</h2>
        <table>
            <tr><td>Тип:</td><td>{data.get('тип_объекта', '—')}</td></tr>
            <tr><td>Площадь:</td><td>{data.get('площадь_квм', 0):,} м²</td></tr>
            <tr><td>Срок:</td><td>~{data.get('срок_месяцев', '—')} мес.</td></tr>
        </table>
        <h2>Расчёт</h2>
        <table>
            <tr><th>Статья</th><th>Сумма, ₽</th></tr>
            <tr><td>Базовая стоимость</td><td>{data.get('базовая_стоимость', 0):,.0f}</td></tr>
    """
    for c in data.get('коэффициенты', []):
        html += f"<tr><td>{c['название']} (+{c['процент']}%)</td><td>+{c['сумма']:,.0f}</td></tr>"
    for d in data.get('скидки', []):
        html += f"<tr><td>{d['название']} (-{d['процент']}%)</td><td>-{d['сумма']:,.0f}</td></tr>"
    html += f"<tr><td><b>ИТОГО</b></td><td><b>{data.get('итоговая_стоимость', 0):,.0f}</b></td></tr></table>"
    html += "<p>ООО «СтройИнвест», Курск</p></body></html>"
    
    return pdfkit.from_string(html, False, configuration=config)

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏗️ *Генератор КП | СтройИнвест*\n\n"
        "Я помогу рассчитать коммерческое предложение на строительство.\n\n"
        "📝 *Отправьте текст:* _Офис 500 кв.м., бизнес-класс, центр Курска, срочно_\n"
        "🎤 *Или запишите голосовое сообщение*\n"
        "📄 В ответ получите расчёт и PDF-документ.",
        parse_mode="Markdown"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or context.user_data.get("voice_text", "")
    if not user_text:
        return
    
    await update.message.reply_text("⏳ Считаю...")
    
    try:
        resp = calculate_kp(user_text)
        s, e = resp.find('{'), resp.rfind('}') + 1
        if s != -1 and e > s:
            data = json.loads(resp[s:e])
            
            answer = f"""
📊 *Расчёт готов!*

🏢 *{data.get('тип_объекта', 'Объект')}*
📐 Площадь: {data.get('площадь_квм', 0):,} м²
💰 Базовая стоимость: {data.get('базовая_стоимость', 0):,.0f} ₽
💵 *Итоговая стоимость: {data.get('итоговая_стоимость', 0):,.0f} ₽*
📅 Срок: ~{data.get('срок_месяцев', '—')} мес.

_{data.get('комментарий', '')}_
"""
            await update.message.reply_text(answer, parse_mode="Markdown")
            
            # PDF
            pdf_data = generate_pdf(data)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name
            await update.message.reply_document(document=open(tmp_path, "rb"), filename=f"KP_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
            os.remove(tmp_path)
        else:
            await update.message.reply_text("❌ Не удалось рассчитать. Попробуйте переформулировать запрос.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Распознаю речь...")
    
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        tmp_path = tmp.name
    
    import subprocess
    wav_path = tmp_path.replace(".ogg", ".wav")
    subprocess.run(["ffmpeg", "-i", tmp_path, wav_path, "-y"], capture_output=True)
    
    load_dotenv()
    client = OpenAI(api_key=os.getenv("VSEGPT_API_KEY"), base_url="https://api.vsegpt.ru/v1")
    with open(wav_path, "rb") as af:
        transcript = client.audio.transcriptions.create(model="stt-openai/whisper-1", file=af, language="ru")
    
    os.remove(tmp_path)
    os.remove(wav_path)
    
    user_text = transcript.text
    context.user_data["voice_text"] = user_text
    await update.message.reply_text(f"📝 Распознано: {user_text}\n⏳ Считаю...")
    await handle_text(update, context)

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🤖 Бот запущен! Напишите ему в Telegram.")
    app.run_polling()

if __name__ == "__main__":
    main()