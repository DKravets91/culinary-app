import streamlit as st
import pandas as pd
import re


@st.cache_data
def load_and_parse(csv_path):
    """Считываем старый файл (3 колонки),
       а затем на лету выделяем 'Количество' и 'Категория'."""
    df_old = pd.read_csv(csv_path)

    # Удаляем лишние пробелы в названиях столбцов, если есть
    df_old.columns = df_old.columns.str.strip()

    # Проверяем, что нужные столбцы присутствуют
    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_old.columns)
    if missing:
        # Если чего-то не хватает, вернём пустой DataFrame и сообщение
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe_name = row["Рецепт"].strip()
        instruction = row["Инструкция"]

        # Имеем одну строку с ингредиентами (может содержать несколько ингредиентов,
        # разделяемых символом новой строки)
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # Поиск количества (пример: "100 г", "2 шт.", "50 мл", "1 щепотка")
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Поиск категории (предположим, она в скобках: "Творог 5% (молочные продукты)")
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # Уберём количество и категорию из названия ингредиента
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean)
            ing_clean = ing_clean.strip(" -")

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean.strip(),
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    df_new = pd.DataFrame(new_rows)
    return df_new


def main():
    st.title("Кулинарный помощник 🍳")

    # 1. Загружаем исходный CSV (3 колонки), парсим в DataFrame (5 колонок)
    df = load_and_parse("recipes.csv")

    if df.empty:
        return  # если парсинг не удался

    st.header("🔍 Поиск рецептов по ингредиенту")
    ingredient_search = st.text_input("Введите ингредиент для поиска:")
    if ingredient_search:
        filtered = df[df["Ингредиент"].str.contains(ingredient_search, case=False, na=False)]
        if not filtered.empty:
            st.subheader("🍽️ Найденные рецепты:")
            grouped = filtered.groupby("Рецепт")
            for recipe_name, group in grouped:
                st.markdown(f"## {recipe_name}")
                st.markdown("**Ингредиенты:**")
                for _, row in group.iterrows():
                    st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
                st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        else:
            st.write("😔 Рецепты с этим ингредиентом не найдены.")

    st.header("📋 Все рецепты")
    all_grouped = df.groupby("Рецепт")
    for recipe_name, group in all_grouped:
        st.markdown(f"### {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
