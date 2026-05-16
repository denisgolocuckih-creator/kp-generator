import streamlit as st
import os
import json
import tempfile
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import pandas as pd
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go
import hashlib

st.set_page_config(page_title="Генератор КП | СтройИнвест", page_icon="🏗️", layout="wide")
load_dotenv()

# ========== ПУТИ ==========
HISTORY_FILE = "data/history.json"
USERS_FILE = "data/users.json"

# ========== АВТОРИЗАЦИЯ ==========
def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def check_password(username, password):
    users = load_users()
    if username in users:
        return users[username]["password"] == password
    return False

def get_user_info(username):
    users = load_users()
    return users.get(username, None)

def init_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "price_list" not in st.session_state:
        st.session_state.price_list = load_default_price_list()
    if "price_source" not in st.session_state:
        st.session_state.price_source = "Стандартный прайс-лист (Курск)"
    if "history" not in st.session_state:
        st.session_state.history = load_all_history() if st.session_state.get("authenticated") else []
    if "user_request" not in st.session_state:
        st.session_state.user_request = ""

# ========== ДАННЫЕ ==========
@st.cache_data
def load_default_price_list():
    with open("data/prices.txt", "r", encoding="utf-8") as f:
        return f.read()

@st.cache_data
def load_company_info():
    with open("data/company_info.txt", "r", encoding="utf-8") as f:
        return f.read()

def load_all_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_all_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_user_history():
    all_history = load_all_history()
    if st.session_state.user_info and st.session_state.user_info["role"] == "admin":
        return all_history
    return [h for h in all_history if h.get("_user") == st.session_state.username]

def add_to_history(data):
    all_history = load_all_history()
    data["_user"] = st.session_state.username
    all_history.append(data)
    save_all_history(all_history)
    st.session_state.history = get_user_history()

def clear_all_history():
    save_all_history([])
    st.session_state.history = []

def clear_user_history():
    all_history = load_all_history()
    all_history = [h for h in all_history if h.get("_user") != st.session_state.username]
    save_all_history(all_history)
    st.session_state.history = []

company_info = load_company_info()
init_session()

# ========== СТРАНИЦА ВХОДА ==========
if not st.session_state.authenticated:
    st.title("🏗️ Генератор КП | СтройИнвест")
    st.markdown("### 🔐 Вход в систему")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("👤 Логин", placeholder="Введите логин")
        password = st.text_input("🔑 Пароль", type="password", placeholder="Введите пароль")
        
        if st.button("🚪 Войти", type="primary", use_container_width=True):
            if check_password(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_info = get_user_info(username)
                st.session_state.history = get_user_history()
                st.rerun()
            else:
                st.error("❌ Неверный логин или пароль")
    
    st.divider()
    st.caption("💡 Тестовые пользователи:")
    st.caption("• admin / admin123 (видит все КП)")
    st.caption("• manager1 / manager123 (только свои КП)")
    st.caption("• manager2 / manager456 (только свои КП)")
    st.caption("• director / director789 (видит все КП)")
    st.stop()

# ========== ИИ ==========
def get_llm():
    return ChatOpenAI(
        model="deepseek/deepseek-chat",
        temperature=0.1,
        openai_api_key=os.getenv("VSEGPT_API_KEY"),
        openai_api_base="https://api.vsegpt.ru/v1"
    )

def calculate_kp(user_input):
    prompt = f"""
Ты — ИИ-калькулятор строительной компании. Твоя задача: выдать ТОЧНЫЙ математический расчёт.

=== БАЗА ЗНАНИЙ (ЦЕНЫ И КОЭФФИЦИЕНТЫ) ===
{st.session_state.price_list}
=== КОНЕЦ БАЗЫ ===

=== ДАННЫЕ КОМПАНИИ ===
{company_info}
=== КОНЕЦ ДАННЫХ ===

АЛГОРИТМ РАСЧЁТА (ВЫПОЛНЯЙ ПО ШАГАМ):
Шаг 1. Найди в базе точную базовую ставку для указанного типа объекта и класса.
Шаг 2. Базовая стоимость = Площадь × Базовая ставка.
Шаг 3. Коэффициенты удорожания применяй ПОСЛЕДОВАТЕЛЬНО (каждый к базе, итог нарастающим).
Шаг 4. Скидки применяй ПОСЛЕДОВАТЕЛЬНО к итогу после коэффициентов.
Шаг 5. Срок строительства = Площадь / 50. Округли до целого вверх.

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

def generate_word(data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    header = doc.sections[0].header
    h_para = header.paragraphs[0]
    h_para.text = "ООО «СтройИнвест» | Курск | +7 (4712) 123-45-67 | info@stroyinvest46.ru"
    h_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h_para.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(128, 128, 128)
    
    title = doc.add_heading('КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    date_para.add_run(f"Дата: {datetime.now().strftime('%d.%m.%Y')}").font.size = Pt(10)
    
    doc.add_paragraph()
    doc.add_heading('Объект строительства', level=2)
    info_table = doc.add_table(rows=5, cols=2, style='Light List Accent 1')
    info_table.cell(0, 0).text = "Тип объекта:"
    info_table.cell(0, 1).text = str(data.get("тип_объекта", "—"))
    info_table.cell(1, 0).text = "Площадь:"
    info_table.cell(1, 1).text = f"{data.get('площадь_квм', 0):,} м²".replace(",", " ")
    info_table.cell(2, 0).text = "Срок строительства:"
    info_table.cell(2, 1).text = f"~{data.get('срок_месяцев', '—')} мес."
    info_table.cell(3, 0).text = "Город:"
    info_table.cell(3, 1).text = "Курск"
    info_table.cell(4, 0).text = "Менеджер:"
    info_table.cell(4, 1).text = st.session_state.user_info["name"] if st.session_state.user_info else "—"
    
    doc.add_paragraph()
    doc.add_heading('Расчёт стоимости', level=2)
    cost_table = doc.add_table(rows=1, cols=4, style='Light Grid Accent 1')
    for cell, text in zip(cost_table.rows[0].cells, ["Статья", "Ставка / %", "Сумма, ₽", "Итого, ₽"]):
        cell.text = text
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    
    base_rate = data.get("базовая_ставка_за_квм", 0)
    base_cost = data.get("базовая_стоимость", 0)
    
    row = cost_table.add_row().cells
    row[0].text = f"Базовая стоимость ({data.get('площадь_квм', 0)} м² × {base_rate:,} ₽/м²)".replace(",", " ")
    row[1].text = "—"
    row[2].text = f"{base_cost:,.0f}".replace(",", " ")
    row[3].text = f"{base_cost:,.0f}".replace(",", " ")
    
    current = base_cost
    for c in data.get("коэффициенты", []):
        current += c["сумма"]
        row = cost_table.add_row().cells
        row[0].text = c["название"]
        row[1].text = f"+{c['процент']}%"
        row[2].text = f"{c['сумма']:,.0f}".replace(",", " ")
        row[3].text = f"{current:,.0f}".replace(",", " ")
    
    for d in data.get("скидки", []):
        current -= d["сумма"]
        row = cost_table.add_row().cells
        row[0].text = d["название"]
        row[1].text = f"-{d['процент']}%"
        row[2].text = f"-{d['сумма']:,.0f}".replace(",", " ")
        row[3].text = f"{current:,.0f}".replace(",", " ")
    
    row = cost_table.add_row().cells
    row[0].text = "ИТОГО"
    row[3].text = f"{data.get('итоговая_стоимость', 0):,.0f}".replace(",", " ")
    for cell in row:
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    
    doc.add_paragraph()
    if data.get("комментарий"):
        doc.add_heading('Примечания', level=2)
        doc.add_paragraph(data["комментарий"])
    
    doc.add_paragraph()
    doc.add_heading('Реквизиты исполнителя', level=2)
    doc.add_paragraph("ООО «СтройИнвест»")
    doc.add_paragraph("ИНН: 4632123456 | КПП: 463201001")
    doc.add_paragraph("305000, г. Курск, ул. Ленина, д. 15, офис 301")
    doc.add_paragraph("Тел.: +7 (4712) 123-45-67 | Email: info@stroyinvest46.ru")
    doc.add_paragraph()
    doc.add_paragraph(f"Менеджер: {st.session_state.user_info['name'] if st.session_state.user_info else '—'}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_excel(history):
    if not history:
        return None
    rows = []
    for h in history:
        coeffs = ", ".join([f"{c['название']} (+{c['процент']}%)" for c in h.get("коэффициенты", [])])
        discounts = ", ".join([f"{d['название']} (-{d['процент']}%)" for d in h.get("скидки", [])])
        rows.append({
            "Менеджер": h.get("_user", ""),
            "Дата": h.get("_время", ""),
            "Тип объекта": h.get("тип_объекта", ""),
            "Площадь, м²": h.get("площадь_квм", 0),
            "Базовая ставка, ₽/м²": h.get("базовая_ставка_за_квм", 0),
            "Базовая стоимость, ₽": h.get("базовая_стоимость", 0),
            "Коэффициенты": coeffs,
            "Итоговая стоимость, ₽": h.get("итоговая_стоимость", 0),
            "Срок, мес.": h.get("срок_месяцев", 0),
        })
    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Все КП")
        ws = writer.sheets["Все КП"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
    buffer.seek(0)
    return buffer

# ========== БОКОВАЯ ПАНЕЛЬ ==========
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/building.png", width=80)
    st.title("🏗️ СтройИнвест")
    
    user_name = st.session_state.user_info["name"] if st.session_state.user_info else "Гость"
    user_role = st.session_state.user_info["role"] if st.session_state.user_info else ""
    st.markdown(f"👤 **{user_name}**")
    st.caption(f"Роль: {user_role} | Логин: {st.session_state.username}")
    
    if st.button("🚪 Выйти", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()
    st.markdown("**ИИ-генератор КП v7.0**")
    st.divider()
    
    st.markdown("### 📊 Прайс-лист")
    st.caption(f"Активен: **{st.session_state.price_source}**")
    
    uploaded_file = st.file_uploader("Загрузите прайс-лист:", type=["xlsx", "csv", "txt"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".txt"):
                st.session_state.price_list = uploaded_file.read().decode("utf-8")
            elif uploaded_file.name.endswith(".csv"):
                st.session_state.price_list = pd.read_csv(uploaded_file).to_string(index=False)
            elif uploaded_file.name.endswith(".xlsx"):
                st.session_state.price_list = pd.read_excel(uploaded_file).to_string(index=False)
            st.session_state.price_source = f"📁 {uploaded_file.name}"
            st.success(f"✅ Загружен")
        except Exception as e:
            st.error(f"Ошибка: {e}")
    
    if st.button("🔄 Сбросить", use_container_width=True):
        st.session_state.price_list = load_default_price_list()
        st.session_state.price_source = "Стандартный"
        st.rerun()
    
    st.divider()
    st.markdown("### 📋 Примеры:")
    for ex in ["Офис 500 кв.м., бизнес-класс, центр, срочно", "Склад 2000 кв.м., тёплый, эконом", "Коттедж 350 кв.м., элитный, зима"]:
        if st.button(ex, use_container_width=True):
            st.session_state.user_request = ex
    
    st.divider()
    if st.session_state.history:
        excel_buffer = generate_excel(st.session_state.history)
        st.download_button("📥 Excel (все КП)", excel_buffer, f"КП_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    
    st.divider()
    st.caption(f"© 2026 СтройИнвест | Сохранено: {len(st.session_state.history)} КП")

# ========== ВКЛАДКИ ==========
tab_main, tab_analytics = st.tabs(["🧮 Калькулятор КП", "📊 Аналитика"])

with tab_main:
    st.title("🧠 Генератор коммерческих предложений")
    st.markdown("Опишите объект или **надиктуйте голосом**.")
    
    st.markdown("### 🎤 Голосовой ввод")
    audio = mic_recorder(start_prompt="🎤 Начать запись", stop_prompt="⏹️ Остановить", just_once=True, use_container_width=True, key="mic")
    
    if audio and audio.get("bytes"):
        with st.spinner("🎙️ Распознаю..."):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio["bytes"])
                temp_path = f.name
            client = OpenAI(api_key=os.getenv("VSEGPT_API_KEY"), base_url="https://api.vsegpt.ru/v1")
            with open(temp_path, "rb") as af:
                transcript = client.audio.transcriptions.create(model="stt-openai/whisper-1", file=af, language="ru")
            os.remove(temp_path)
            st.session_state.user_request = transcript.text
            st.rerun()
    
    user_request = st.text_area("📝 Описание объекта:", value=st.session_state.user_request, placeholder="Офис 500 кв.м., бизнес-класс, центр...", height=100)
    
    c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 2])
    with c3:
        btn = st.button("🚀 Рассчитать КП", type="primary", use_container_width=True)
    with c5:
        if st.button("🗑️ Очистить", use_container_width=True):
            st.session_state.user_request = ""
            st.rerun()
    
    if btn and user_request:
        with st.spinner("⏳ Считаю..."):
            try:
                resp = calculate_kp(user_request)
                s, e = resp.find('{'), resp.rfind('}') + 1
                if s != -1 and e > s:
                    data = json.loads(resp[s:e])
                    data["_время"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    add_to_history(data)
                    st.success("✅ Готово!")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🏢 Тип", data.get("тип_объекта", "—"))
                    c2.metric("📐 Площадь", f"{data.get('площадь_квм', 0):,} м²".replace(",", " "))
                    c3.metric("💰 Итого", f"{data.get('итоговая_стоимость', 0):,.0f} ₽".replace(",", " "))
                    
                    st.divider()
                    t1, t2, t3, t4 = st.tabs(["📋 Сводка", "📈 Коэфф.", "🏷️ Скидки", "🏢 Контакты"])
                    with t1:
                        br = data.get("базовая_ставка_за_квм", 0)
                        bc = data.get("базовая_стоимость", 0)
                        af = data.get("стоимость_после_коэффициентов", "—")
                        ca, cb = st.columns(2)
                        ca.metric("Базовая ставка", f"{br:,} ₽/м²".replace(",", " "))
                        ca.metric("Базовая стоимость", f"{bc:,.0f} ₽".replace(",", " "))
                        cb.metric("После коэфф.", f"{af:,.0f} ₽".replace(",", " ") if isinstance(af, (int, float)) else af)
                        cb.metric("Итого", f"{data.get('итоговая_стоимость', 0):,.0f} ₽".replace(",", " "))
                        st.metric("📅 Срок", f"~{data.get('срок_месяцев', '—')} мес.")
                        st.info(data.get("комментарий", "—"))
                    with t2:
                        for c in data.get("коэффициенты", []):
                            st.write(f"• {c['название']}: +{c['процент']}% (+{c['сумма']:,.0f} ₽)".replace(",", " "))
                    with t3:
                        for d in data.get("скидки", []):
                            st.write(f"• {d['название']}: -{d['процент']}% (-{d['сумма']:,.0f} ₽)".replace(",", " "))
                    with t4:
                        st.write("ООО «СтройИнвест», Курск")
                    
                    st.divider()
                    dc1, dc2, dc3 = st.columns(3)
                    dc1.download_button("📥 JSON", json.dumps(data, ensure_ascii=False, indent=2), f"KP_{datetime.now().strftime('%H%M')}.json", use_container_width=True)
                    dc2.download_button("📄 Word", generate_word(data), f"KP_{datetime.now().strftime('%H%M')}.docx", use_container_width=True)
            except Exception as ex:
                st.error(f"Ошибка: {ex}")
    
    st.divider()
    st.caption("💡 Голосовой ввод — в Chrome.")

# ========== АНАЛИТИКА ==========
with tab_analytics:
    st.title("📊 Аналитика")
    
    if not st.session_state.history:
        st.info("Сделайте расчёты в калькуляторе.")
    else:
        df = pd.DataFrame(st.session_state.history)
        
        total_kp = len(df)
        total_sum = df["итоговая_стоимость"].sum()
        avg_check = df["итоговая_стоимость"].mean()
        avg_area = df["площадь_квм"].mean()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 КП", total_kp)
        m2.metric("💰 Сумма", f"{total_sum:,.0f} ₽".replace(",", " "))
        m3.metric("💵 Средний", f"{avg_check:,.0f} ₽".replace(",", " "))
        m4.metric("📐 Площадь", f"{avg_area:,.0f} м²".replace(",", " "))
        
        # Статистика по менеджерам (для админа)
        if st.session_state.user_info and st.session_state.user_info["role"] == "admin":
            st.divider()
            st.markdown("### 👥 Статистика по менеджерам")
            if "_user" in df.columns:
                user_stats = df.groupby("_user").agg(
                    Количество=("итоговая_стоимость", "count"),
                    Общая_сумма=("итоговая_стоимость", "sum"),
                    Средний_чек=("итоговая_стоимость", "mean")
                ).reset_index()
                st.dataframe(user_stats, use_container_width=True, hide_index=True)
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if "тип_объекта" in df.columns:
                tc = df["тип_объекта"].value_counts().reset_index()
                tc.columns = ["Тип", "Кол-во"]
                fig1 = px.pie(tc, values="Кол-во", names="Тип", hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
        with c2:
            if "тип_объекта" in df.columns:
                dg = df.groupby("тип_объекта")["итоговая_стоимость"].sum().reset_index()
                fig2 = px.bar(dg, x="тип_объекта", y="итоговая_стоимость", color="тип_объекта")
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
        
        st.divider()
        st.dataframe(df[["_user", "_время", "тип_объекта", "площадь_квм", "итоговая_стоимость"]].tail(10), use_container_width=True, hide_index=True)
        
        if st.session_state.user_info and st.session_state.user_info["role"] == "admin":
            if st.button("🗑️ Очистить ВСЮ историю", use_container_width=True):
                clear_all_history()
                st.rerun()
        else:
            if st.button("🗑️ Очистить мою историю", use_container_width=True):
                clear_user_history()
                st.rerun()