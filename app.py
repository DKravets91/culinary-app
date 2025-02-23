import streamlit as st
import pandas as pd

@st.cache_data
def load_data(csv_path: str):
    """Загружаем CSV и возвращаем DataFrame."""
    df = pd.read_csv(csv_path)
    # Убираем случайные пробелы в названиях столбцов
    df.columns = df.columns.str.strip()
    return df

def main():
    st.title("Кулинарный помощник 🍳")

    # 1. Загружаем данные из файла recipes.csv
    recipes_df = load_data("recipes.csv")

    # 2. Показываем список столбцов для диагностики
    st.write("Название столбцов:", list(recipes_df.columns))

    # 3. Проверяем, есть ли нужные столбцы
    required_cols = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = required_cols - set(recipes_df.columns)
    if missing:
        st.error(f"Не найдены обязательные столбцы: {missing}")
        return

    # 4. Поиск по ингредиенту
    st.header("🔍 Поиск рецептов по ингредиенту")
    ingredient_search = st.text_input("Введите ингредиент для поиска:")
    if ingredient_search:
        # Фильтруем по столбцу "Ингредиенты"
        filtered = recipes_df[recipes_df["Ингредиенты"].str.contains(ingredient_search, case=False, na=False)]
        if not filtered.empty:
            st.subheader("🍽️ Найденные рецепты:")
            # Группируем по названию рецепта
            grouped = filtered.groupby("Рецепт")
            for recipe_name, group in grouped:
                st.markdown(f"## {recipe_name}")
                st.markdown("**Ингредиенты:**")
                for _, row in group.iterrows():
                    st.markdown(f"- {row['Ингредиенты']}")
                st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        else:
            st.write("😔 Рецепты с этим ингредиентом не найдены.")

    # 5. Отображение всех рецептов
    st.header("📋 Все рецепты")
    all_grouped = recipes_df.groupby("Рецепт")
    for recipe_name, group in all_grouped:
        st.markdown(f"### {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            st.markdown(f"- {row['Ингредиенты']}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
