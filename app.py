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
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # 1) Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # 2) Ищем категорию
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # 3) Очищаем название ингредиента от (категории) и самого количества
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean).strip()

            # Убираем дефис, если он остался одиноко
            # например, "Яйца — ..." превращаем в "Яйца"
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?", " ", ing_clean)
            ing_clean = ing_clean.strip()

            new_rows.append({
                "Рецепт": recipe,
                "Ингредиент": ing_clean,
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

    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")

    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            ing = row["Ингредиент"]
            qty = row["Количество"]
            cat = row["Категория"]

            # Аккуратно склеиваем
            qty_part = f" — {qty}" if qty else ""
            cat_part = f" ({cat})" if cat else ""

            st.markdown(f"- {ing}{qty_part}{cat_part}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
