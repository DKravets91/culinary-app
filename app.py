import streamlit as st
import pandas as pd
import re


#########################################################
# ФУНКЦИИ
#########################################################

def parse_quantity(qty_str: str):
    """
    Преобразует строку вида '100 г' или '2 шт' в (число, единица).
    Возвращает (0.0, '') если не удалось распарсить.
    """
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip())
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        return (num, unit)
    return (0.0, "")


@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    """
    Считываем старый CSV (3 колонки: Рецепт, Ингредиенты, Инструкция)
    и на лету создаём DataFrame со столбцами:
    [Рецепт, Ингредиент, Количество, Категория, Инструкция].

    Для диагностики выводим отладочную информацию.
    """
    # Шаг 1: читаем исходный CSV
    df_old = pd.read_csv(csv_path)

    # Показываем изначальные столбцы
    st.write("Изначальные столбцы из CSV:", list(df_old.columns))

    # Удаляем лишние пробелы в названиях
    df_old.columns = df_old.columns.str.strip()

    # Проверяем, что колонки [Рецепт, Ингредиенты, Инструкция] есть
    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_old.columns)
    if missing:
        st.error(f"Не найдены обязательные столбцы: {missing}")
        return pd.DataFrame()

    # Шаг 2: Парсим "Ингредиенты" на несколько строк
    new_rows = []
    for _, row in df_old.iterrows():
        recipe_name = str(row["Рецепт"]).strip()
        instruction = str(row["Инструкция"])

        # Разделяем строку "Ингредиенты" по новой строке (или `;`, если так у тебя)
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # Ищем количество (пример: '100 г', '2 шт', ...)
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Ищем категорию в скобках
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # Очищаем название ингредиента от (категория) и кол-ва
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean)

            # Убираем возможные дефисы и точки в конце
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    # Создаём новый DataFrame
    df_new = pd.DataFrame(new_rows)

    # Для диагностики выводим названия столбцов и первые строки
    st.write("Итоговые столбцы после парсинга:", list(df_new.columns))
    st.dataframe(df_new.head(10))

    return df_new


def sum_ingredients(selected_df):
    """
    Суммируем ингредиенты (числовые).
    Для каждой строки парсим Количество (например, '100 г'),
    затем группируем по [Ингредиент, Единица].
    """
    parsed_list = []
    for _, row in selected_df.iterrows():
        ing = row["Ингредиент"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        parsed_list.append({
            "Ингредиент": ing,
            "Количество_число": num,
            "Единица": unit
        })

    tmp_df = pd.DataFrame(parsed_list)
    grouped = tmp_df.groupby(["Ингредиент", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped


#########################################################
# ОСНОВНАЯ ФУНКЦИЯ
#########################################################

def main():
    st.title("Кулинарный помощник 🍳")

    # Загружаем и парсим CSV (3->5 колонок)
    df = load_and_parse("recipes.csv")

    # Если парсинг не удался (df пуст) — прерываем
    if df.empty:
        return

    st.header("🔍 Выберите несколько рецептов для суммирования:")
    recipes_list = df["Рецепт"].unique().tolist()
    selected = st.multiselect("Выберите рецепты:", recipes_list)

    if selected:
        # Фильтруем DataFrame
        selected_df = df[df["Рецепт"].isin(selected)]

        # Суммируем
        summed_df = sum_ingredients(selected_df)
        st.write("### Итоговый список ингредиентов:")
        for _, row_sum in summed_df.iterrows():
            ing = row_sum["Ингредиент"]
            num = row_sum["Количество_число"]
            unit = row_sum["Единица"]
            if unit:
                st.markdown(f"- **{ing}**: {num} {unit}")
            else:
                st.markdown(f"- **{ing}**: {num}")
        st.write("---")

    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")
    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row_ing in group.iterrows():
            ing = row_ing["Ингредиент"]
            qty = row_ing["Количество"]
            cat = row_ing["Категория"]

            qty_part = f" — {qty}" if qty else ""
            cat_part = f" ({cat})" if cat else ""
            st.markdown(f"- {ing}{qty_part}{cat_part}")

        # Инструкция
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
