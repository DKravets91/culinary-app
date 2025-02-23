import streamlit as st
import pandas as pd
import re

###################################################################
# СИНОНИМЫ И АВТОГРУППЫ
###################################################################
SYNONYMS = {
    # При желании можно добавить другие
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
    "яйц": "яйца",       # если встречаем «яйц» (в т.ч. «яйца», «яйцо»), ставим группу «яйца»
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

###################################################################
def unify_ingredient_name(original_name: str):
    """
    Очищаем «(категория c1)» из названия, если хотим.
    Но пользователь сказал: «Яйца (категория c1)» оставить.
    Тогда мы их не трогаем, только применим синонимы при необходимости.
    """
    # Если хотите совсем вырезать (категория c1) из названия, раскомментируйте:
    # original_name = re.sub(r"\(категория\s*c\d\)", "", original_name, flags=re.IGNORECASE)
    # original_name = re.sub(r"категория\s*c\d", "", original_name, flags=re.IGNORECASE)
    name = original_name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

###################################################################
def auto_assign_group(ing_name: str) -> str:
    """
    Поиск группы по AUTO_GROUPS.
    Если ing_name содержит «яйца (категория c1)», всё равно внутри есть «яйц», значит «яйца».
    """
    ing_lower = ing_name.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

###################################################################
@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_old.columns)
    if missing:
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    new_rows = []
    for _, row in df_old.iterrows():
        recipe_name = str(row["Рецепт"]).strip()
        instruction = str(row["Инструкция"])
        ing_list = str(row["Ингредиенты"]).split("\n")

        for ing in ing_list:
            ing_lower = ing.lower().strip()
            if not ing_lower or "для начинки" in ing_lower:
                continue

            # Количество
            qty_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0) if qty_match else ""

            # Пробуем вытащить группу из скобок — если написано (молочные продукты) и т.п.
            group_match = re.search(r"\((.*?)\)", ing)
            group_str = group_match.group(1) if group_match else ""

            # Убираем количество из названия, но оставляем (категория c1) если есть
            name_no_qty = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing, flags=re.IGNORECASE)
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            # Приводим к нижнему регистру, применяем синонимы
            ing_clean = unify_ingredient_name(name_no_qty)

            # Если group_str не пусто, используем его, иначе auto_assign
            if not group_str:
                group_str = auto_assign_group(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty.strip(),  # ОРИГИНАЛ, включая «(категория c1)»
                "Количество": quantity.strip(),
                "Группа": group_str.strip().lower(),
                "Инструкция": instruction
            })

    df_new = pd.DataFrame(new_rows)
    return df_new

###################################################################
def sum_ingredients(selected_df: pd.DataFrame):
    rows = []
    for _, row in selected_df.iterrows():
        orig_name = row["Ингредиент"]
        grp = row["Группа"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        rows.append({
            "Ингредиент": orig_name,
            "Группа": grp,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(rows)
    grouped = tmp_df.groupby(["Ингредиент", "Группа", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

###################################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        # «Порции» теперь храним в отдельной колонке
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","Ингредиент","Количество","Группа","Инструкция"])

    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # У каждой строки в cart будет своя «Порции»
    extended = selected_rows.copy()
    extended["Порции"] = portions
    st.session_state["cart"] = pd.concat([st.session_state["cart"], extended], ignore_index=True)

def remove_recipe_from_cart(recipe_name):
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

###################################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    #--- Поиск по ингредиенту
    st.header("Поиск по ингредиенту")
    ing_search = st.text_input("Введите название ингредиента:")
    if ing_search:
        found = df[df["Ингредиент"].str.contains(ing_search.lower(), case=False, na=False)]
        if not found.empty:
            st.subheader("Рецепты, где встречается этот ингредиент:")
            for rcp in found["Рецепт"].unique():
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено рецептов с таким ингредиентом.")
        st.write("---")

    #--- Добавление рецептов
    st.header("Добавить рецепты в список (с учётом порций)")
    rec_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""] + rec_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)
            st.success(f"Добавлен рецепт: {recipe_choice} x {portions} порций!")

    #--- Отображение выбранных рецептов
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"]
        # Группируем по рецепту, суммируем «Порции»
        recipe_groups = cart_df.groupby("Рецепт")["Порции"].sum().reset_index()
        for _, r_row in recipe_groups.iterrows():
            rcp_name = r_row["Рецепт"]
            sum_portions = r_row["Pорции"]  # check the column name carefully
            st.markdown(f"- **{rcp_name}** (всего порций: {sum_portions})")
            # Кнопка удаления
            if st.button(f"Удалить «{rcp_name}»"):
                remove_recipe_from_cart(rcp_name)
                st.success(f"«{rcp_name}» удалён!")
                return  # выходим, перерендерим

        st.write("---")

        # Итоговый список ингредиентов
        st.write("### Итоговый список ингредиентов (по группам)")
        summed = sum_ingredients(cart_df)
        grouped = summed.groupby("Группа")
        for grp_name in sorted(grouped.groups.keys()):
            sub_cat = grouped.get_group(grp_name)
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

    #--- Все рецепты
    st.header("Все рецепты (оригинал)")
    grouped_df = df.groupby("Рецепт")
    for rname, group in grouped_df:
        st.markdown(f"## {rname}")
        st.markdown("**Ингредиенты:**")
        for _, r_ing in group.iterrows():
            ing = r_ing["Ингредиент"]
            qty = r_ing["Количество"]
            qpart = f" — {qty}" if qty else ""
            st.markdown(f"- {ing}{qpart}")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
