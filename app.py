import streamlit as st
import pandas as pd
import re


@st.cache_data
def load_and_parse(csv_path):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    needed_cols = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed_cols - set(df_old.columns)
    if missing:
        st.error(f"Не найдены обязательные столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe = row["Рецепт"].strip()
        instruction = row["Инструкция"]

        # Разделяем возможные строки ингредиентов по новой строке '\n'
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Ищем категорию в скобках
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # Очищаем название ингредиента
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean)
            ing_clean = ing_clean.strip(" -")

            new_rows.append({
                "Рецепт": recipe,
                "Ингредиент": ing_clean.strip(),
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)


def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

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
                    ing = row["Ингредиент"]
                    qty = row["Количество"]
                    cat = row["Категория"]

                    # Формируем строку аккуратно
                    qty_part = f" — {qty}" if qty else ""
                    cat_part = f" ({cat})" if cat else ""

                    st.markdown(f"- {ing}{qty_part}{cat_part}")

                st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        else:
            st.write("😔 Рецепты с этим ингредиентом не найдены.")

    st.header("📋 Все рецепты")
    all_grouped = df.groupby("Рецепт")
    for recipe_name, group in all_grouped:
        st.markdown(f"### {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            ing = row["Ингредиент"]
            qty = row["Количество"]
            cat = row["Категория"]

            # Формируем строку аккуратно
            qty_part = f" — {qty}" if qty else ""
            cat_part = f" ({cat})" if cat else ""

            st.markdown(f"- {ing}{qty_part}{cat_part}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
