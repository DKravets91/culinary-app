import streamlit as st
import pandas as pd

# Загрузка структурированных рецептов из CSV с явным переносом строк
recipes_df = pd.read_csv('updated_recipes_with_cherry.csv')

# Преобразуем ингредиенты, чтобы они отображались с новой строки
recipes_df['Ингредиенты'] = recipes_df['Ингредиенты'].apply(lambda x: x.replace(') ', ')\n'))


# Заголовок приложения
st.title("Кулинарный помощник 🍳")

# Поиск по ингредиенту
st.header("🔍 Поиск рецептов по ингредиенту")
ingredient = st.text_input("Введите ингредиент для поиска:")

if ingredient:
    # Фильтрация рецептов по ингредиенту
    filtered_recipes = recipes_df[recipes_df['Ингредиенты'].str.contains(ingredient, case=False, na=False)]
    if not filtered_recipes.empty:
        st.subheader("🍽️ Найденные рецепты:")
        for _, row in filtered_recipes.iterrows():
            st.markdown(f"## {row['Название']}")
            st.write(f"**Ингредиенты:**\n{row['Ингредиенты']}")
            st.write(f"**Инструкция:**\n{row['Инструкция']}")
    else:
        st.write("😔 Рецепты с этим ингредиентом не найдены.")

# Отображение всех рецептов
st.header("📋 Все рецепты")
for _, row in recipes_df.iterrows():
    st.markdown(f"### {row['Название']}")
    # Разделяем ингредиенты по запятым и закрывающей скобке
    ingredients = row['Ингредиенты'].replace(') ', ')\n').replace(', ', '\n- ')
    st.markdown(f"**Ингредиенты:**\n- {ingredients}")
    st.write(f"**Инструкция:**\n{row['Инструкция']}")



