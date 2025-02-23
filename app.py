import streamlit as st
import pandas as pd
import re

#########################################################
# ШАГ 1. СЛОВАРИ ДЛЯ УНИФИКАЦИИ
#########################################################

# Синонимы: приводим разные варианты к одному названию
SYNONYMS = {
    "мука пшеничная": "пшеничная мука",
    "пшеничная мука": "пшеничная мука",
    "яйца (категория c1)": "яйца",
    "яйцо куриное": "яйца",
    "яйца": "яйца",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",  # В auto_categories укажем, что это "специи и приправы"
}

# Автокатегории: если нет категории, ищем подстроку
AUTO_CATEGORIES = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",
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
    "микс сушёных трав": "специи и приправы",
    "для начинки": "",  # Будем отфильтровывать
    "виш": "ягоды",
    "шоколад": "кондитерские изделия",
}


#########################################################
# ПАРСЕР КОЛИЧЕСТВА
#########################################################
def parse_quantity(qty_str: str):
    """
    '100 г' -> (100.0, 'г')
    '2 шт' -> (2.0, 'шт')
    Если не получилось — (0.0, '')
    """
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")


#########################################################
# УНИФИКАЦИЯ НАЗВАНИЯ ИНГРЕДИЕНТА
#########################################################
def unify_ingredient_name(name: str):
    name = name.strip().lower()
    # Если встречаем "категория c1" и т.п., вырезаем это
    name = re.sub(r"(категория\s*c\d)", "", name)
    # Убираем синонимы
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()


#########################################################
# АВТО-ПОДСТАВКА КАТЕГОРИИ
#########################################################
def auto_assign_category(ing: str):
    ing_lower = ing.lower()
    for key_sub, cat_name in AUTO_CATEGORIES.items():
        if key_sub in ing_lower:
            return cat_name
    return ""


#########################################################
# ПАРСИМ CSV (Рецепт, Ингредиенты, Инструкция) -> (Рецепт, Ингредиент, Количество, Категория, Инструкция)
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
            ing_lower = ing.lower().strip()
            if not ing_lower or ing_lower == "для начинки":
                # Пропускаем пустые строчки и "для начинки"
                continue

            # 1) Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = quantity_match.group(0) if quantity_match else ""

            # 2) Ищем категорию в скобках
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # 3) Очищаем название
            ing_clean = re.sub(r"\(.*?\)", "", ing, flags=re.IGNORECASE)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean, flags=re.IGNORECASE)
            # Убираем двойные тире, точки
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            # 4) Унифицируем (яйцо -> яйца, мука пшеничная -> пшеничная мука, и т.п.)
            ing_clean = unify_ingredient_name(ing_clean)

            # 5) Автокатегория, если не было вытащено из скобок
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
        cat = row["Категория"]
        num, unit = parse_quantity(qty_str)
        parsed_list.append({
            "Ингредиент": ing,
            "Категория": cat,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(parsed_list)

    # Группируем по [Ингредиент, Категория, Единица]
    grouped = tmp_df.groupby(["Ингредиент", "Категория", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped


def main():
    st.title("Кулинарный помощник 🍳")

    # ЗАГРУЗКА и ПАРСИНГ
    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    # --- ПОИСК ПО ИНГРЕДИЕНТУ (новое поле)
    st.header("Поиск по ингредиенту")
    ingredient_search = st.text_input("Введите название ингредиента (например, 'яйца' или 'мак'):")
    if ingredient_search:
        filtered = df[df["Ингредиент"].str.contains(ingredient_search.lower(), case=False, na=False)]
        if not filtered.empty:
            st.subheader("Рецепты, где встречается этот ингредиент:")
            # Сгруппируем по рецепту
            for recipe_name in filtered["Рецепт"].unique():
                st.markdown(f"- **{recipe_name}**")
        else:
            st.write("Не найдено рецептов с таким ингредиентом.")
        st.write("---")

    # --- ВЫБОР НЕСКОЛЬКИХ РЕЦЕПТОВ ДЛЯ СУММИРОВАНИЯ
    st.header("Суммарный список ингредиентов для выбранных рецептов")
    recipes_list = df["Рецепт"].unique().tolist()
    selected = st.multiselect("Выберите рецепты:", recipes_list)

    if selected:

