import streamlit as st
import pandas as pd
import re


# Функция парсинга количества: "100 г" -> (100, "г"), "2 шт" -> (2, "шт")
def parse_quantity(qty_str: str):
    # Ищем что-то вроде: число + пробел + единица (г|гр|шт|мл и т.п.)
    match = re.match(r"(\d+)\s?(г|гр|шт|мл|kg|л|ст\.л|ч\.л|щепотка)", qty_str)
    if match:
        num = float(match.group(1))  # например, "100" -> 100.0
        unit = match.group(2)  # например, "г"
        return (num, unit)
    return (0.0, "")  # Если не удалось распарсить


@st.cache_data
def load_and_parse(csv_path):
    """Предполагаем, что здесь уже парсим «Рецепт», «Ингредиент», «Количество», «Категория».
       Или у нас всего три столбца (Рецепт, Ингредиенты, Инструкция) -> Разбиваем, как раньше.
    """
    # ... Твой код парсинга, тот же что был выше ...
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    # Проверяем, есть ли нужные столбцы...
    # Для краткости предположим, что у нас уже есть: Рецепт, Ингредиент, Количество, Категория, Инструкция
    return df_old


def sum_ingredients(selected_df):
    """
    Принимает DataFrame со столбцами:
      - Ингредиент
      - Количество (в виде строки, например, "100 г")
    Возвращает DataFrame, где ингредиенты сгруппированы и количество суммуется по единице измерения.
    """
    # Разбиваем «Количество» на число и единицу
    parsed = []
    for _, row in selected_df.iterrows():
        ing_name = row["Ингредиент"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        parsed.append({
            "Ингредиент": ing_name,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(parsed)

    # Группируем по (Ингредиент, Единица) и суммируем
    grouped = tmp_df.groupby(["Ингредиент", "Единица"], as_index=False)["Количество_число"].sum()
    # Возвращаем результат
    return grouped


def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    # --- Выбор нескольких рецептов ---
    recipes_list = df["Рецепт"].unique().tolist()
    selected = st.multiselect("Выберите рецепты для суммирования:", recipes_list)

    if selected:
        # Фильтруем DataFrame
        selected_df = df[df["Рецепт"].isin(selected)]

        # Группируем и суммируем ингредиенты
        summed_df = sum_ingredients(selected_df)

        st.write("### Итоговый список ингредиентов:")
        for _, row in summed_df.iterrows():
            ing = row["Ингредиент"]
            num = row["Количество_число"]
            unit = row["Единица"]
            if unit:
                st.markdown(f"- **{ing}**: {num} {unit}")
            else:
                # Если нет единицы (не смогли распарсить), показываем просто число
                st.markdown(f"- **{ing}**: {num}")

        st.write("---")

    # --- Отображение всех рецептов (как раньше) ---
    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")
    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            ing = row["Ингредиент"]
            qty = row["Количество"]
            cat = row.get("Категория", "")

            # Аккуратно формируем строку
            qty_part = f" — {qty}" if qty else ""
            cat_part = f" ({cat})" if cat else ""
            st.markdown(f"- {ing}{qty_part}{cat_part}")

        instruction = group.iloc[0]["Инструкция"]
        st.markdown(f"**Инструкция:**\n{instruction}")
        st.write("---")


if __name__ == "__main__":
    main()
