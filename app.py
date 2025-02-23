import streamlit as st
import pandas as pd
import re

def format_ingredients(ingredients_text: str) -> str:
    """
    Разбивает строку ингредиентов на отдельные пункты.
    Учитывает случаи, когда после 'шт.' сразу идёт новый ингредиент.
    """

    # 1. Ставим перенос строки после ' шт.', если следующее слово начинается с заглавной буквы или цифры.
    #    Пример: "4 шт. Мука" превращаем в "4 шт.\nМука"
    text = re.sub(r"(\d+\s*шт\.)\s+(?=[A-ZА-ЯЁ0-9])", r"\1\n", ingredients_text)

    # 2. "запятая + )" превращаем в ") " (чтобы не слипались)
    text = re.sub(r",\s*\)", ") ", text)

    # 3. Разбиваем по шаблону: ') ' или ','
    #    - \)\s   означает закрывающую скобку + пробел
    #    - ,      означает запятую
    pattern = r"\)\s|,"
    raw_items = re.split(pattern, text)

    # 4. Убираем пустые строки и лишние пробелы
    cleaned = [item.strip() for item in raw_items if item.strip()]

    # 5. Добавляем ')' в конец пункта, если нет
    final_list = []
    for item in cleaned:
        if not item.endswith(")"):
            item += ")"
        final_list.append(item)

    # 6. Формируем список с маркером '- '
    result = "\n- ".join(final_list)
    return f"- {result}"


# Загружаем файл с рецептами
recipes_df = pd.read_csv('updated_recipes_with_cherry.csv')

# Заголовок приложения
st.title("Кулинарный помощник 🍳")

# Поиск по ингредиенту
st.header("🔍 Поиск рецептов по ингредиенту")
ingredient = st.text_input("Введите ингредиент для поиска:")

if ingredient:
    filtered_recipes = recipes_df[
        recipes_df['Ингредиенты'].str.contains(ingredient, case=False, na=False)
    ]
    if not filtered_recipes.empty:
        st.subheader("🍽️ Найденные рецепты:")
        for _, row in filtered_recipes.iterrows():
            st.markdown(f"## {row['Название']}")
            formatted_ingredients = format_ingredients(str(row['Ингредиенты']))
            st.markdown(f"**Ингредиенты:**\n{formatted_ingredients}")
            st.write(f"**Инструкция:**\n{row['Инструкция']}")
    else:
        st.write("😔 Рецепты с этим ингредиентом не найдены.")

# Отображение всех рецептов
st.header("📋 Все рецепты")
for _, row in recipes_df.iterrows():
    st.markdown(f"### {row['Название']}")
    formatted_ingredients = format_ingredients(str(row['Ингредиенты']))
    st.markdown(f"**Ингредиенты:**\n{formatted_ingredients}")
    st.write(f"**Инструкция:**\n{row['Инструкция']}")
