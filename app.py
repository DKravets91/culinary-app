import streamlit as st
import pandas as pd
import re

@st.cache_data
def load_and_parse(csv_path):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    # Проверяем наличие нужных столбцов
    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_old.columns)
    if missing:
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe = row["Рецепт"].strip()
        instruction = row["Инструкция"]
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Ищем категорию
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # Очищаем название
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean)
            # Убираем «лишние» пробелы и дефисы в конце
            ing_clean = ing_clean.strip()
            ing_clean = re.sub(r"[-—]+\s*$", "", ing_clean)  # удаляем '-' или '—' в конце

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

    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")

    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            ing = row["Ингредиент"]
            qty = row["Количество"]
            cat = row["Категория"]

            # Формируем аккуратную строку
            qty_part = f" — {qty}" if qty else ""
            cat_part = f" ({cat})" if cat else ""

            st.markdown(f"- {ing}{qty_part}{cat_part}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
