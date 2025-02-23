import streamlit as st
import pandas as pd
import re

#########################################################
# ШАГ 1. СЛОВАРИ ДЛЯ УНИФИКАЦИИ
#########################################################

# SYNONYMS: приводим разные написания к одному
SYNONYMS = {
    "мука пшеничная": "пшеничная мука",
    "пшеничная мука": "пшеничная мука",
    "яйца (категория c1)": "яйца",
    "яйцо куриное": "яйца",
    "яйца": "яйца",
    # если нужно ещё что-то, добавьте сюда
}

# AUTO_CATEGORIES: если категория не указана, то если в названии ингредиента
# есть определённая подстрока, ставим эту категорию
AUTO_CATEGORIES = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",        # сулугуни => содержит слово "сыр"? или отдельно "сулугуни" : "молочные продукты"
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",      # сливочное масло
    "яйц": "яйца",                     # "яйцо", "яйца"
    "мука": "мука и злаки",
    "крахмал": "мука и злаки",
    "укроп": "овощи и зелень",
    "соль": "специи и приправы",
    "перец": "специи и приправы",
    "ваниль": "специи и приправы",
    "разрыхлитель": "специи и приправы",
    "мак": "специи и приправы",
    "сахар": "специи и приправы",
    "фундук": "орехи",
    "миндаль": "орехи",
    "виш": "ягоды",          # "вишня"
    "шоколад": "кондитерские изделия",
}

#########################################################
# ФУНКЦИЯ ПАРСИНГА КОЛИЧЕСТВА
#########################################################
def parse_quantity(qty_str: str):
    """
    '100 г' -> (100.0, 'г')
    '2 шт' -> (2.0, 'шт')
    Если не получилось — возвращаем (0.0, '')
    """
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

#########################################################
# УНИФИКАЦИЯ НАЗВАНИЯ ИНГРЕДИЕНТА (SYNONYMS)
#########################################################
def unify_ingredient_name(name: str):
    """Приводим к нижнему регистру, убираем пробелы."""
    # Убираем двойные/одиночные тире в конце
    name = name.strip().lower()
    # Проверяем словарь синонимов
    if name in SYNONYMS:
        return SYNONYMS[name]
    return name

#########################################################
# АВТО-ПОДСТАВКА КАТЕГОРИИ (AUTO_CATEGORIES)
#########################################################
def auto_assign_category(ing: str):
    ing_lower = ing.lower()
    for key_sub, cat_name in AUTO_CATEGORIES.items():
        if key_sub in ing_lower:
            return cat_name
    return ""

#########################################################
# ПАРСИМ CSV (3 КОЛОНКИ -> 5 КОЛОНОК)
#########################################################
@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    needed_cols = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed_cols - set(df_old.columns)
    if missing:
        st.error(f"Не найдены обязательные столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe_name = str(row["Рецепт"]).strip()
        instruction = str(row["Инструкция"])
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            # Если встречается строка "для начинки", пропускаем
            ing_lower = ing.lower().strip()
            if ing_lower == "для начинки":
                continue

            # 1) Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = quantity_match.group(0) if quantity_match else ""

            # 2) Ищем категорию в скобках (допустим, (категория C1))
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # 3) Очищаем название
            ing_clean = re.sub(r"\(.*?\)", "", ing, flags=re.IGNORECASE)   # убираем (...)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean, flags=re.IGNORECASE)
            # Убираем двойные тире, точки
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            # 4) Приводим к единообразию
            ing_clean = unify_ingredient_name(ing_clean)

            # 5) Если категория не найдена, пытаемся автоприсвоить
            if not category:
                category = auto_assign_category(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)

#########################################################
# СУММИРУЕМ ИНГРЕДИЕНТЫ
#########################################################
def sum_ingredients(selected_df):
    parsed_list = []
    for _, row in selected_df.iterrows():
        ing = row["Ингредиент"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        # Парсинг категории (если нужно)
        cat = row["Категория"]
        parsed_list.append({
            "Ингредиент": ing,
            "Количество_число": num,
            "Единица": unit,
            "Категория": cat
        })
    tmp_df = pd.DataFrame(parsed_list)

    # Группируем по [Ингредиент, Единица, Категория], чтобы одинаковые ингредиенты суммировались
    grouped = tmp_df.groupby(["Ингредиент", "Единица", "Категория"], as_index=False)["Количество_число"].sum()
    return grouped

#########################################################
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
#########################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    # Блок: выбор нескольких рецептов для суммирования ингредиентов
    st.header("Суммарный список ингредиентов для выбранных рецептов")
    recipes_list = df["Рецепт"].unique().tolist()
    selected = st.multiselect("Выберите рецепты:", recipes_list)

    if selected:
        selected_df = df[df["Рецепт"].isin(selected)]
        summed_df = sum_ingredients(selected_df)

        # Теперь показываем результат, сгруппированный по Категориям
        st.write("### Итоговый список ингредиентов (по категориям):")
        cat_grouped = summed_df.groupby("Категория")
        for cat_name in sorted(cat_grouped.groups.keys()):
            sub_cat = cat_grouped.get_group(cat_name)
            st.markdown(f"#### {cat_name if cat_name else 'Без категории'}")
            for _, row_s in sub_cat.iterrows():
                ing = row_s["Ингредиент"]
                num = row_s["Количество_число"]
                unit = row_s["Единица"]
                line = f"- **{ing}**: {num} {unit}" if unit else f"- **{ing}**: {num}"
                st.markdown(line)
        st.write("---")

    # Блок: отображение всех рецептов (без группировки по категориям)
    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")
    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row_ing in group.iterrows():
            ing = row_ing["Ингредиент"]
            qty = row_ing["Количество"]
            # Не группируем по категориям, просто выводим
            qty_part = f" — {qty}" if qty else ""
            st.markdown(f"- {ing}{qty_part}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
