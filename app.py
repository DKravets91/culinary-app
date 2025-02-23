import streamlit as st
import pandas as pd
import re

###########################################################
# СИНОНИМЫ И АВТОГРУППЫ
###########################################################
SYNONYMS = {
    "яйцо куриное": "яйца",
    "яйца (категория c1)": "яйца",
    "яйца": "яйца",
    "мука пшеничная": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",
}

AUTO_GROUPS = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",
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
    "для начинки": "",
}

###########################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

def unify_ingredient_name(name: str):
    # Убираем '(категория c1)' и т.п.
    name = re.sub(r"\(категория\s*c\d\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"категория\s*c\d", "", name, flags=re.IGNORECASE)
    name = name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

def auto_assign_group(ing: str) -> str:
    ing_lower = ing.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    needed_cols = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed_cols - set(df_old.columns)
    if missing:
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe_name = str(row["Рецепт"]).strip()
        instruction = str(row["Инструкция"])
        ingredients_list = str(row["Ингредиенты"]).split("\n")

        for ing in ingredients_list:
            if not ing.strip() or "для начинки" in ing.lower():
                continue

            # Количество
            qty_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0) if qty_match else ""

            # Группа из скобок?
            group_match = re.search(r"\((.*?)\)", ing)
            group_str = group_match.group(1) if group_match else ""

            # Убираем (с)…, количество…
            ing_clean = re.sub(r"\(.*?\)", "", ing, flags=re.IGNORECASE)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean, flags=re.IGNORECASE)
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            # Унифицируем название (яйцо -> яйца и т.д.)
            ing_clean = unify_ingredient_name(ing_clean)

            # Если group_str похоже на 'категория c1', заменяем на 'яйца'
            if re.match(r"(?i)категория\s*c\d", group_str):
                group_str = "яйца"

            # Если пусто — автоприсваиваем
            if not group_str:
                group_str = auto_assign_group(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)

def sum_ingredients(selected_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in selected_df.iterrows():
        ing = row["Ингредиент"]
        grp = row["Группа"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        rows.append({
            "Ингредиент": ing,
            "Группа": grp,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(rows)
    grouped = tmp_df.groupby(["Ингредиент", "Группа", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт", "Ингредиент", "Количество", "Группа", "Инструкция"])

    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # дублируем строки 'portions' раз
    extended = pd.concat([selected_rows]*portions, ignore_index=True)
    st.session_state["cart"] = pd.concat([st.session_state["cart"], extended], ignore_index=True)

def remove_recipe_from_cart(recipe_name):
    """Удаляем все строки, относящиеся к данному рецепту, из корзины."""
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    ###################################################################
    # 1) Поиск по ингредиенту
    ###################################################################
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

    ###################################################################
    # 2) Добавление рецептов с порциями
    ###################################################################
    st.header("Добавить рецепты в список (с учётом порций)")
    recipes_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", ["" ]+ recipes_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)
            st.success(f"Добавлено: {recipe_choice} x {portions} порций!")

    ###################################################################
    # 3) Отображение выбранных рецептов, возможность удаления
    ###################################################################
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        st.write("### Выбранные рецепты (список)")
        chosen_recs = st.session_state["cart"]["Рецепт"].unique().tolist()
        for rcp in chosen_recs:
            st.markdown(f"- **{rcp}**")
            if st.button(f"Удалить «{rcp}»"):
                remove_recipe_from_cart(rcp)
                st.experimental_rerun()
        st.write("---")

        # Итоговый список ингредиентов
        st.write("### Итоговый список ингредиентов (по группам)")
        final_df = sum_ingredients(st.session_state["cart"])
        grp_grouped = final_df.groupby("Группа")
        for grp_name in sorted(grp_grouped.groups.keys()):
            sub_cat = grp_grouped.get_group(grp_name)
            st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
            for _, row_s in sub_cat.iterrows():
                ing = row_s["Ингредиент"]
                num = row_s["Количество_число"]
                unit = row_s["Единица"]
                if unit:
                    st.markdown(f"- **{ing}**: {num} {unit}")
                else:
                    st.markdown(f"- **{ing}**: {num}")
        st.write("---")

    ###################################################################
    # 4) Все рецепты (оригинал)
    ###################################################################
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
