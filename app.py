import streamlit as st
import pandas as pd
import re

# Функция для форматирования ингредиентов,
# чтобы они отображались в виде списков с новой строки
def format_ingredients(ingredients_text: str) -> str:
    """
    Разбивает строку ингредиентов по скобкам и запятым,
    добавляя переносы строк для удобного чтения.
    """
    # Шаг 1: Заменяем "запятая + скобка" на пробел + скобка, чтобы не склеивались слова
    text = re.sub(r",\s*\)", ") ", ingredients_text)

    # Шаг 2: Разбиваем по шаблону: ') ' или ',' в конце строки
    # r"\)\s|,$" значит:
    # - \)\s : закрывающая скобка и пробел
    # - ,$   : запятая в конце строки
    pattern = r"\)\s|,$"
    raw_items = re.split(pattern, text)

    # Шаг 3: Убираем пустые строки и лишние пробелы
    cleaned = [item.strip() for item in raw_items if item.strip()]

    # Шаг 4: Добавляем закрывающую скобку, если её нет
    final_list = []
    for item in cleaned:
        if not item.endswith(")"):
            item += ")"
        final_list.append(item)

    # Шаг 5: Формируем итоговый список с маркерами '-'
    result = "\n- ".join(final_list)
    return f"- {result}"


# Загрузка структурированных рецептов из CSV
recipes_df = pd.read_csv('updated_recipes_with_cherry.csv')

# Заголовок приложения
st.title("Кулинарный помощник 🍳")

# Поиск по ингредиенту
st.header("🔍 Поиск рецептов по ингредиенту")
ingredient = st.text_input("Введите ингредиент для поиска:")

if ingredient:
    # Фильтрация рецептов по ингредиенту
    filtered_recipes = recipes_df[
        recipes_df['Ингредиенты'].str.contains(ingredient, case=False, na=False)
    ]
    if not filtered_recipes.empty:
        st.subheader("🍽️ Найденные рецепты:")
        for _, row in filtered_recipes.iterrows():
            st.markdown(f"## {row['Название']}")
            # Форматируем ингредиенты и выводим
            formatted_ingredients = format_ingredients(str(row['Ингредиенты']))
            st.markdown(f"**Ингредиенты:**\n{formatted_ingredients}")
            st.write(f"**Инструкция:**\n{row['Инструкция']}")
    else:
        st.write("😔 Рецепты с этим ингредиентом не найдены.")

# Отображение всех рецептов
st.header("📋 Все рецепты")
for _, row in recipes_df.iterrows():
    st.markdown(f"### {row['Название']}")
    # Используем функцию format_ingredients для красивого вывода
    formatted_ingredients = format_ingredients(str(row['Ингредиенты']))
    st.markdown(f"**Ингредиенты:**\n{formatted_ingredients}")
    st.write(f"**Инструкция:**\n{row['Инструкция']}")
