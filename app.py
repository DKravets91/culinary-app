import streamlit as st
import pandas as pd

# Загрузка данных из файла recipes.csv
recipes_df = pd.read_csv('recipes.csv')

# Убираем лишние пробелы из названий столбцов
recipes_df.columns = recipes_df.columns.str.strip()

# Проверка названий столбцов
st.write("Названия столбцов в файле:", list(recipes_df.columns))

# Заголовок приложения
st.title("Кулинарный помощник 🍳")

# Поиск по ингредиенту
st.header("🔍 Поиск рецептов по ингредиенту")
ingredient = st.text_input("Введите ингредиент для поиска:")

if ingredient:
    filtered_recipes = recipes_df[recipes_df['Ингредиент'].str.contains(ingredient, case=False, na=False)]
    if not filtered_recipes.empty:
        st.subheader("🍽️ Найденные рецепты:")
        for _, row in filtered_recipes.iterrows():
            st.markdown(f"## {row['Рецепт']}")  # Заменили 'Название' на 'Рецепт'
            st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
            st.write(f"**Инструкция:**\n{row['Инструкция']}")
    else:
        st.write("😔 Рецепты с этим ингредиентом не найдены.")

# Отображение всех рецептов
st.header("📋 Все рецепты")

# Вывод всех названий рецептов
if "Рецепт" in recipes_df.columns:
    grouped = recipes_df.groupby("Рецепт")  # Группируем по 'Рецепт'
    for recipe_name, group in grouped:
        st.markdown(f"### {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
        instruction = group["Инструкция"].iloc[0]
        st.markdown(f"**Инструкция:**\n{instruction}")
else:
    st.write("❌ Столбец 'Рецепт' не найден в данных. Пожалуйста, проверьте структуру файла recipes.csv.")
