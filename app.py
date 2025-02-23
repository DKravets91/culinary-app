import streamlit as st
import pandas as pd
import re

###################################################################
# СИНОНИМЫ И АВТОКАТЕГОРИИ
###################################################################
SYNONYMS = {
    "яйцо куриное": "яйца",
    "яйца (категория c1)": "яйца",
    "яйца": "яйца",
    "мука пшеничная": "пшеничная мука",
    "пшеничная мука": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",
}

AUTO_CATEGORIES = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",   # «яйцо», «яйца»
    "мука": "мука и злаки",
    "крахмал": "мука и злаки",
    "разрыхлитель": "мука и злаки",
    "укроп": "овощи и зелень",
    "соль": "специи и приправы",
    "перец": "специи и приправы",
    "ваниль": "специи и приправы",
    "мак": "специи и приправы",
    "сахар": "специи и приправы",
    "фундук": "орехи",
    "миндаль": "орехи",
    "микс сушёных трав": "специи и приправы",
    "виш": "ягоды",
    "шоколад": "кондитерские изделия",
    "для начинки": "",  # пропускаем
}

###################################################################
def parse_quantity(qty_str: str):
    """
    '100 г' -> (100.0, 'г')
    '2 шт' -> (2.0, 'шт')
    """
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

def unify_ingredient_name(name: str):
    """
    Убираем 'категория c...' и унифицируем через SYNONYMS.
    """
    # Удаляем вхождения «(категория c1)» в названии
    name = re.sub(r"\(категория\s*c\d\)", "", name, flags=re.IGNORECASE)
    # Удаляем «категория c\d» где-нибудь ещё
    name = re.sub(r"категория\s*c\d", "", name, flags=re.IGNORECASE)
    name = name.strip().lower()

    # Если есть в словаре синонимов — приводим
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

def auto_assign_category(ing: str) -> str:
    ing_lower = ing.lower()
    for key_sub, cat_name in AUTO_CATEGORIES.items():
        if key_sub in ing_lower:
            return cat_name
    return ""

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
            ing_low = ing.lower().strip()
            if not ing_low or ing_low == "для начинки":
                continue

            # Количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Категория из скобок?
            cat_match = re.search(r"\((.*?)\)", ing)
            cat_str = cat_match.group(1) if cat_match else ""

            # Очищаем название
            ing_clean = re.sub(r"\(.*?\)", "", ing, flags=re.IGNORECASE)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean, flags=re.IGNORECASE)
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            # Унифицируем название
            ing_clean = unify_ingredient_name(ing_clean)

            # Если cat_str начинается с «категория c»
            if re.match(r"(?i)категория\s*c\d", cat_str):
                cat_str = "яйца"

            # Если пустая — автоназначаем
            if not cat_str:
                cat_str = auto_assign_category(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,
                "Количество": quantity.strip(),
                "Категория": cat_str.strip(),
                "Инструкция": instruction
            })
    return pd.DataFrame(new_rows)

def sum_ingredients(selected_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in selected_df.iterrows():
        ing = row["Ингредиент"]
        cat = row["Категория"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        rows.append({
            "Ингредиент": ing,
            "Категория": cat,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(rows)
    # Группируем по (Ингредиент, Категория, Единица)
    grouped = tmp_df.groupby(["Ингредиент", "Категория", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт", "Ингредиент", "Количество", "Категория", "Инструкция"])

    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # Дублируем строки 'portions' раз
    extended = pd.concat([selected_rows]*portions, ignore_index=True)
    # Объединяем
    st.session_state["cart"] = pd.concat([st.session_state["cart"], extended], ignore_index=True)

def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    # Поиск по ингредиенту
    st.header("Поиск по ингредиенту")
    ingredient_search = st.text_input("Введите название ингредиента:")
    if ingredient_search:
        filtered = df[df["Ингредиент"].str.contains(ingredient_search.lower(), case=False, na=False)]
        if not filtered.empty:
            st.subheader("Рецепты, где встречается этот ингредиент:")
            for rcp in filtered["Рецепт"].unique():
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено рецептов с таким ингредиентом.")
        st.write("---")

    # Выбор рецептов c порциями
    st.header("Добавить рецепты в список (с учётом порций)")
    recipes_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", ["" ]+ recipes_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)
            st.success(f"Добавлено: {recipe_choice} x {portions} порций!")

    # Итоговый список ингредиентов (по категориям)
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        st.write("### Итоговый список ингредиентов (по категориям)")
        final_df = sum_ingredients(st.session_state["cart"])
        cat_grouped = final_df.groupby("Категория")
        for cat_name in sorted(cat_grouped.groups.keys()):
            sub_cat = cat_grouped.get_group(cat_name)
            st.markdown(f"#### {cat_name if cat_name else 'Без категории'}")
            for _, row_s in sub_cat.iterrows():
                ing = row_s["Ингредиент"]
                num = row_s["Количество_число"]
                unit = row_s["Единица"]
                if unit:
                    st.markdown(f"- **{ing}**: {num} {unit}")
                else:
                    st.markdown(f"- **{ing}**: {num}")
        st.write("---")

    st.header("Все рецепты (оригинал)")
    grouped = df.groupby("Рецепт")
    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row_ing in group.iterrows():
            ing = row_ing["Ингредиент"]
            qty = row_ing["Количество"]
            qty_part = f" — {qty}" if qty else ""
            st.markdown(f"- {ing}{qty_part}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
