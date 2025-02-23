import streamlit as st
import pandas as pd
import re

###################################################################
# СИНОНИМЫ И АВТОГРУППЫ
###################################################################
SYNONYMS = {
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
    "яйц": "яйца",  # «яйца», «яйцо», «(категория c1)»
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
# parse_quantity : «100 г» -> (100, "г")
###################################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

###################################################################
# unify_ingredient_name : приведение к нижнему регистру, SYNONYMS
###################################################################
def unify_ingredient_name(original_name: str) -> str:
    name = original_name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

###################################################################
# auto_assign_group : поиск в словаре AUTO_GROUPS
###################################################################
def auto_assign_group(ing_name: str) -> str:
    ing_lower = ing_name.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

###################################################################
# load_and_parse : CSV (3 cols) -> DF (Рецепт, Порции, Ингредиент, Количество, Группа, Инструкция)
###################################################################
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
            ing_low = ing.lower().strip()
            if not ing_low or "для начинки" in ing_low:
                continue

            # Определяем количество (например, "100 г")
            qty_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0) if qty_match else ""

            # Убираем только количество из названия (оставляя (категория c1) при желании)
            name_no_qty = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing, flags=re.IGNORECASE)
            # Убираем лишние тире, точки
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            ing_clean = unify_ingredient_name(name_no_qty)

            # Автоприсвоение группы
            group_str = auto_assign_group(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty.strip(),
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)

###################################################################
# sum_ingredients : суммируем ингредиенты (учёт порций через дублирование строк)
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
# add_recipe_to_cart : при добавлении P порций -> дублируем строки
###################################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","Ингредиент","Количество","Группа","Инструкция"])

    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # Дублируем каждую строку «portions» раз
    extended = pd.concat([selected_rows]*portions, ignore_index=True)
    extended["Порции"] = 1  # У каждой строки порция=1
    st.session_state["cart"] = pd.concat([st.session_state["cart"], extended], ignore_index=True)

###################################################################
# remove_recipe_from_cart : удаляем строки выбранного рецепта
###################################################################
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

    #=== Поиск по ингредиенту И / ИЛИ группе
    st.header("Поиск ингредиентов или групп")
    search_text = st.text_input("Введите название ингредиента или группы:")
    if search_text:
        # Делаем нижний регистр для поиска
        low_search = search_text.lower()
        # Фильтруем по совпадению в полях 'Ингредиент' ИЛИ 'Группа'
        found = df[
            df["Ингредиент"].str.lower().str.contains(low_search, na=False)
            | df["Группа"].str.lower().str.contains(low_search, na=False)
        ]
        if not found.empty:
            st.subheader("Рецепты с этим ингредиентом / группой:")
            for rcp in found["Рецепт"].unique():
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено.")
        st.write("---")

    #=== Добавление рецептов
    st.header("Добавить рецепты в список (с учётом порций)")
    rec_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""] + rec_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)
            st.success(f"Добавлен рецепт: {recipe_choice} x {portions} порций!")

    #=== Отображение выбранных рецептов
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"]
        # Для каждого рецепта подсчитаем, сколько раз (строк) он добавлен
        recipe_counts = cart_df.groupby("Рецепт").size().reset_index(name="Count")

        for _, r_row in recipe_counts.iterrows():
            rcp_name = r_row["Рецепт"]
            total_portions = r_row["Count"]
            # количество строк = NINGREDIENTS * P (каждая строка = 1)
            # Если нужно показывать именно P, надо разделить total_portions на кол-во ингредиентов
            # в df_parsed[df_parsed["Рецепт"] == rcp_name] (смотри пример выше)

            st.markdown(f"- **{rcp_name}** (всего порций: {total_portions})")
            if st.button(f"Удалить «{rcp_name}»"):
                remove_recipe_from_cart(rcp_name)
                st.success(f"«{rcp_name}» удалён!")
                return

        st.write("---")

        # Итоговый список ингредиентов (по группам)
        st.write("### Итоговый список ингредиентов (по группам)")
        final_df = sum_ingredients(cart_df)
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

    #=== Все рецепты
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
