import streamlit as st

st.set_page_config(page_title="Генератор КП | Умные сметы за секунды", page_icon="🏗️", layout="wide")

# ========== ШАПКА ==========
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.title("🏗️ Генератор коммерческих предложений")
    st.markdown("### ИИ-калькулятор для строительных компаний")
    st.markdown("Создавайте точные сметы и КП **за 30 секунд** с помощью искусственного интеллекта.")
    st.divider()

# ========== ГЛАВНЫЙ БЛОК ==========
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🚀 Что умеет программа?")
    st.markdown("""
    - 🎤 **Голосовой ввод** — надиктуйте описание объекта
    - 🧮 **Автоматический расчёт** — ИИ подбирает ставки, коэффициенты, скидки
    - 📄 **Экспорт в Word, PDF, Excel, 1С** — готовые документы за секунду
    - 📊 **Аналитика и воронка продаж** — отслеживайте эффективность менеджеров
    - 👥 **Многопользовательский режим** — у каждого менеджера своя история
    - 🔒 **Защита и лицензирование** — привязка к компьютеру, шифрование
    
    **Время на одно КП: с 3 часов → 30 секунд.**
    """)

with col_right:
    st.markdown("### 📊 Пример расчёта")
    st.markdown("**Запрос:** *Офис 500 кв.м., бизнес-класс, центр Курска, срочно*")
    
    # Пример таблицы
    import pandas as pd
    example = pd.DataFrame({
        "Статья": ["Базовая стоимость", "Срочный заказ (+25%)", "Центр города (+15%)", "ИТОГО"],
        "Сумма, ₽": ["14 000 000", "+3 500 000", "+2 100 000", "19 600 000"]
    })
    st.dataframe(example, use_container_width=True, hide_index=True)
    st.caption("Результат за 5 секунд. Экспорт в Word, PDF, 1С — одна кнопка.")

# ========== ПРЕИМУЩЕСТВА ==========
st.divider()
st.markdown("### 💎 Почему выбирают нас")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("⚡", "30 секунд")
    st.caption("На создание одного КП")
with c2:
    st.metric("📄", "4 формата")
    st.caption("Word, PDF, Excel, 1С")
with c3:
    st.metric("🎤", "Голос")
    st.caption("Ввод голосом")
with c4:
    st.metric("🔒", "Защита")
    st.caption("Привязка к ПК")

# ========== ТАРИФЫ ==========
st.divider()
st.markdown("### 💰 Тарифы")

tc1, tc2, tc3 = st.columns(3)

with tc1:
    st.markdown("#### 🎁 Демо")
    st.markdown("**14 дней бесплатно**")
    st.markdown("- Все функции\n- Без ограничений\n- Техподдержка")
    st.markdown("**0 ₽**")

with tc2:
    st.markdown("#### ⭐ Базовый")
    st.markdown("**1 год лицензии**")
    st.markdown("- 3 менеджера\n- Все форматы экспорта\n- Аналитика\n- Обновления")
    st.markdown("**от 50 000 ₽**")

with tc3:
    st.markdown("#### 👑 Корпоративный")
    st.markdown("**Бессрочная лицензия**")
    st.markdown("- Безлимит менеджеров\n- Интеграция с 1С\n- Индивидуальная доработка\n- VIP-поддержка")
    st.markdown("**от 150 000 ₽**")

# ========== ФОРМА ЗАЯВКИ ==========
st.divider()
st.markdown("### 📩 Оставить заявку")

col_f1, col_f2, col_f3 = st.columns([1, 2, 1])
with col_f2:
    name = st.text_input("Ваше имя:")
    phone = st.text_input("Телефон или Email:")
    if st.button("🚀 Отправить заявку", type="primary", use_container_width=True):
        if name and phone:
            # Сохраняем заявку в файл
            with open("data/leads.txt", "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {name} | {phone}\n")
            st.success("✅ Заявка принята! Мы свяжемся с вами в ближайшее время.")
        else:
            st.error("Заполните все поля.")

# ========== ПОДВАЛ ==========
st.divider()
st.markdown("#### 📞 Контакты")
st.markdown("Email: **denisgolocuckih@gmail.com** | Telegram: **@ArcWarden243**")
st.caption("© 2026 Генератор КП. Все права защищены.")