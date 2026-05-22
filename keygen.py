import streamlit as st
from datetime import datetime
import pandas as pd
import hashlib

# ========== ЗАГРУЖАЕМ СЕКРЕТЫ ==========
try:
    from secret import SECRET_SALT
except ImportError:
    st.error("🔒 secret.py не найден. Генератор ключей не запустится без секретного файла.")
    st.stop()

# ========== ГЕНЕРАТОР КЛЮЧЕЙ ==========
def generate_license_key(days, hardware_id):
    expire_date = (datetime.now() + pd.Timedelta(days=days)).strftime('%Y.%m.%d')
    raw = f"KP-{days}-{expire_date}-{hardware_id}-{SECRET_SALT}"
    signature = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return f"KP-{days}-{expire_date}-{hardware_id}-{signature}"

# ========== ИНТЕРФЕЙС ==========
st.set_page_config(page_title="Генератор ключей | KP-Gen", page_icon="🔑", layout="centered")
st.title("🔑 Генератор лицензионных ключей")
st.markdown("Генерация ключей для программы **«Генератор КП»**")
st.divider()

# Поля ввода
col1, col2 = st.columns(2)
with col1:
    days = st.number_input("Срок действия (дней):", min_value=1, max_value=3650, value=365, step=30)
with col2:
    tariff = st.selectbox("Тариф:", ["Демо (14 дн.)", "Месяц (30 дн.)", "Квартал (90 дн.)", "Полгода (180 дн.)", "Год (365 дн.)", "2 года (730 дн.)", "3 года (1095 дн.)"])

# Автозаполнение дней из тарифа
tariff_days = {"Демо (14 дн.)": 14, "Месяц (30 дн.)": 30, "Квартал (90 дн.)": 90, "Полгода (180 дн.)": 180, "Год (365 дн.)": 365, "2 года (730 дн.)": 730, "3 года (1095 дн.)": 1095}
if tariff in tariff_days:
    days = tariff_days[tariff]

hardware_id = st.text_input("ID компьютера клиента:", placeholder="C1A2B3D4E5F6A7B8", help="Клиент видит этот ID на странице активации.")
client_name = st.text_input("Имя клиента / компании (для заметки):", placeholder="ООО «Ромашка»")

if st.button("🔑 Сгенерировать ключ", type="primary", use_container_width=True):
    if hardware_id and len(hardware_id) >= 4:
        key = generate_license_key(days, hardware_id)
        expire_date = (datetime.now() + pd.Timedelta(days=days)).strftime('%d.%m.%Y')
        
        st.success("✅ Ключ сгенерирован!")
        st.code(key, language="text")
        
        # Информация о ключе
        st.markdown(f"""
        **📋 Информация о ключе:**
        - 🖥️ ID компьютера: `{hardware_id}`
        - 📅 Срок действия: **{days} дн.** (до {expire_date})
        - 👤 Клиент: {client_name or '—'}
        """)
        
        # Кнопка копирования
        st.button("📋 Копировать ключ", on_click=lambda: st.write(key))
        
        # История (сохраняется в сессии)
        if "key_history" not in st.session_state:
            st.session_state.key_history = []
        st.session_state.key_history.append({
            "Дата": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "Клиент": client_name or "—",
            "Дней": days,
            "До": expire_date,
            "HWID": hardware_id,
            "Ключ": key
        })
    else:
        st.error("Введите корректный ID компьютера (минимум 4 символа).")

# История ключей
if "key_history" in st.session_state and st.session_state.key_history:
    st.divider()
    st.markdown("### 📜 История сгенерированных ключей")
    df = pd.DataFrame(st.session_state.key_history)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Кнопка очистки
    if st.button("🗑️ Очистить историю"):
        st.session_state.key_history = []
        st.rerun()

st.divider()
st.caption("🔒 Генератор ключей — только для разработчика. Не передавайте третьим лицам.")