import streamlit as st
import pandas as pd
import re

###########################################################
# СИНОНИМЫ И АВТОГРУППЫ
###########################################################
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
    "яйц": "яйца",       # «яйца (категория c1)» => группа «яйца»
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
# Парсинг «100 г» -> (100, "г")
###########################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

###########################################################
# Унификация названия ингредиента
###########################################################
def unify_ingredient_name(original_name: str) -> str:
    """
    Не вырезаем «(категория c1)»,
    только приводим к нижнему регистру и применяем синонимы, если есть.
    """
    name = original_name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

###########################################################
# Автоматическая группа
###########################################################
def auto_assign_group(ing_name: str) -> str:
    ing_lower = ing_name.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

###########################################################
# Загрузка и парсинг CSV (3 -> 5 колонок)
###########################################################
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

            # Количество
            qty_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0) if qty_match else ""

            # Попробуем вытащить группу из скобок
            group_match = re.search(r"\((.*?)\)", ing)
            group_str = group_match.group(1) if group_match else ""

            # Убираем количество из названия, но не удаляем (категория c1)...
            name_no_qty = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing, flags=re.IGNORECASE)
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            ing_clean = unify_ingredient_name(name_no_qty)

            # Если group_str пусто -> auto_assign
            group_str = group_str.lower()
            if re.search(r"категория\s*c\d", group_str):
                group_str = "яйца"
            if not group_str:
                group_str = auto_assign_group(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty.strip(),
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)

###########################################################
# Суммируем ингредиенты (учитывая «Порции» как множитель)
###########################################################
def sum_ingredients(cart_df: pd.DataFrame):
    # Каждый рецепт хранит «Порции». При умножении ингредиентов = Pорции * parse_quantity
    rows = []
    for _, row in cart_df.iterrows():
        # умножаем parse_quantity(qty_str) на row["Порции"]
        portions = row["Порции"]
        orig_name = row["Ингредиент"]
        grp = row["Группа"]
        qty_str = row["Количество"]
        base_num, unit = parse_quantity(qty_str)
        num = base_num * portions  # Умножаем на кол-во порций
        rows.append({
            "Ингредиент": orig_name,
            "Группа": grp,
            "Количество_число": num,
            "Единица": unit
        })
    tmp_df = pd.DataFrame(rows)
    grouped = tmp_df.groupby(["Ингредиент", "Группа", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

###########################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(
            columns=["Рецепт","Порции","Ингредиент","Количество","Группа","Инструкция"]
        )

    # Ищем строки этого рецепта
    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # Проверяем, есть ли уже такой рецепт в cart
    cart = st.session_state["cart"]
    existing_index = cart[cart["Рецепт"] == recipe_name].index

    if not existing_index.empty:
        # Уже есть этот рецепт, тогда просто увеличим «Порции»
        idx = existing_index[0]
        old_portions = cart.loc[idx, "Порции"]
        new_portions = old_portions + portions
        st.session_state["cart"].loc[idx, "Порции"] = new_portions
        st.success(f"У рецепта «{recipe_name}» теперь {new_portions} порций!")
    else:
        # Добавляем одну запись для рецепта
        # В ней надо хранить суммарно ингредиенты? — Нет, сами ингредиенты все
        # Но по ТЗ: User не хочет каждую строку дублировать,
        # => Храним ровно одну строку per ингредиент?
        # => Упростим: Храним ровно 1 строку PER рецепт,
        #    а у ингредиентов parse_quantity * portions.
        # Но тогда мы потеряем детали ингредиентов…

        # Чтобы хранить ровно 1 строку, придётся «сливать» все ингредиенты в одну запись.
        # Однако удобнее хранить ингредиенты построчно.
        # Раз ТЗ гласит «У каждой строки порция=1, но строка дублироваться не надо» —
        # мы сделаем проще: для каждого рецепта — ОДНА строка, 'Порции' = X, 'Ингредиенты' = ... ???

        # Однако в предыдущих сообщениях логика была,
        # что df_parsed содержит много строк (по ингредиенту).
        # Если хотим 1 строку per рецепт, придётся «сливать» ингредиенты.

        # !!! Упростим: храним 1 строку на рецепт,
        # => ingredients_list / quantity_list / group_list => ?

        # Но TЗ "не дублировать строки" — подразумевает,
        #   что cart имеет 1 строку per рецепт,
        #   а итоговый parse делаем "на лету"?
        # Ok, давайте.

        #  => Сольём df_parsed по этому рецепту => JSON
        #  => 'Порции' = portions

        # Сольём все ингредиенты / количества / группы в JSON для 1 строки
        ing_json = selected_rows.to_dict(orient="records")
        # ing_json — список словарей (Ингредиент, Количество, Группа, ...)
        # Храним одним словарём
        row_data = {
            "Рецепт": recipe_name,
            "Порции": portions,
            "Ингредиент": ing_json,  # список словарей
            "Количество": "",        # пусто, т.к. для каждого своя
            "Группа": "",            # пусто, у нас разное
            "Инструкция": selected_rows.iloc[0]["Инструкция"]
        }
        st.session_state["cart"] = st.session_state["cart"].append(row_data, ignore_index=True)
        st.success(f"Добавлен рецепт «{recipe_name}» x {portions} порций!")

def remove_recipe_from_cart(recipe_name):
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

###########################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    #=== Поиск
    st.header("Поиск по ингредиенту")
    ing_search = st.text_input("Введите название ингредиента:")
    if ing_search:
        found = df[df["Ингредиент"].str.contains(ing_search.lower(), case=False, na=False)]
        if not found.empty:
            st.subheader("Рецепты с этим ингредиентом:")
            for rcp in found["Рецепт"].unique():
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено рецептов с таким ингредиентом.")
        st.write("---")

    #=== Добавление рецептов
    st.header("Добавить рецепты в список (с учётом порций)")
    rec_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""] + rec_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)

    #=== Список выбранных рецептов
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"].copy()

        # Группируем по названию рецепта, суммируя 'Порции'
        grouped_recipes = cart_df.groupby("Рецепт")["Порции"].sum().reset_index()

        for _, rrow in grouped_recipes.iterrows():
            rcp_name = rrow["Рецепт"]
            total_port = rrow["Порции"]
            st.markdown(f"- **{rcp_name}** (всего порций: {total_port})")
            if st.button(f"Удалить «{rcp_name}»"):
                remove_recipe_from_cart(rcp_name)
                st.success(f"«{rcp_name}» удалён!")
                return
        st.write("---")

        #=== Итоговый список ингредиентов (по группам)
        st.write("### Итоговый список ингредиентов (по группам)")
        # Нужно «на лету» собрать все ингредиенты из cart (JSON), умножить на «Порции».
        rows = []
        for _, crow in cart_df.iterrows():
            recipe_name = crow["Рецепт"]
            portions = crow["Порции"]
            ing_json = crow["Ингредиент"]
            if isinstance(ing_json, list):
                # Это список словарей
                for ing_entry in ing_json:
                    ing_name = ing_entry["Ингредиент"]
                    grp = ing_entry["Группа"]
                    qty_str = ing_entry["Количество"]
                    base, unit = parse_quantity(qty_str)
                    total = base * portions
                    rows.append({
                        "Рецепт": recipe_name,
                        "Ингредиент": ing_name,
                        "Группа": grp,
                        "Количество_число": total,
                        "Единица": unit
                    })
            else:
                # иначе нет ингредиентов
                pass
        if rows:
            final_df = pd.DataFrame(rows)
            grouped_final = final_df.groupby(["Ингредиент","Группа","Единица"], as_index=False)["Количество_число"].sum()
            # group by group
            group_cat = grouped_final.groupby("Группа")
            for grp_name in sorted(group_cat.groups.keys()):
                sub = group_cat.get_group(grp_name)
                st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
                for _, frow in sub.iterrows():
                    ing = frow["Ингредиент"]
                    num = frow["Количество_число"]
                    unt = frow["Единица"]
                    if unt:
                        st.markdown(f"- **{ing}**: {num} {unt}")
                    else:
                        st.markdown(f"- **{ing}**: {num}")
        else:
            st.write("Пока ингредиентов нет.")
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
