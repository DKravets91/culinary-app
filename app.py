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
    "яйц": "яйца",  # для «яйца (категория c1)» и т.п.
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

###################################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

def unify_ingredient_name(original_name: str) -> str:
    name = original_name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

def auto_assign_group(ing_name: str) -> str:
    ing_lower = ing_name.lower()
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

    # Сохраним в поле «ингредиенты» список словарей
    #   [{Ингредиент, Количество, Группа}, ...]
    # По одному рецепту -> одна строка,
    # но, если CSV содержит одну строку на КАЖДЫЙ ингредиент, придётся сливать.
    # Однако в предыдущих итерациях у нас 1 рецепт = много строк.
    # Тогда «сливать» их по рецепту.
    # ИЛИ CSV на самом деле 3 столбца,
    #   => parse -> много строк?
    #   => cливаем…

    # Но в предыдущих версиях мы уже преобразовывали.
    # Здесь упростим: CSV (3 колонки) -> parse ->
    #   ... Actually, user wants 1 row = 1 recipe.
    #   => нам нужно groupby recipe_name -> list of ingredients.

    # Сгруппируем «старый parse» (многострочное) -> 1 строка:
    #   recipe_name | [ {ing, qty, group}, ... ] | инструкция
    # Для этого надо сначала «parse» ingredient by line,
    #   потом groupby.

    # 1) Парсим post-line
    parse_rows = []
    for idx, line in df_old.iterrows():
        rcp = line["Рецепт"].strip()
        instruction = line["Инструкция"]
        lines_ing = str(line["Ингредиенты"]).split("\n")

        for ing in lines_ing:
            if not ing.strip() or "для начинки" in ing.lower():
                continue
            qty_match = re.search(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0).strip() if qty_match else ""

            # group in parentheses?
            group_match = re.search(r"\((.*?)\)", ing)
            group_str = group_match.group(1) if group_match else ""

            # remove numeric from name but keep (категория c1) if present
            name_no_qty = re.sub(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing, flags=re.IGNORECASE)
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            ing_clean = unify_ingredient_name(name_no_qty)
            group_str = group_str.lower()
            # If it contains "категория c1" -> "яйца"
            if re.search(r"категория\s*c\d", group_str, re.IGNORECASE):
                group_str = "яйца"
            if not group_str:
                group_str = auto_assign_group(ing_clean)

            parse_rows.append({
                "Рецепт": rcp,
                "Ингредиент": name_no_qty.strip(),
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    # Теперь parse_rows — многострочный. Groupby по "Рецепт", сливаем ингредиенты в list of dict
    parse_df = pd.DataFrame(parse_rows)
    if parse_df.empty:
        return pd.DataFrame()

    recipes = []
    grouped = parse_df.groupby("Рецепт")
    for rname, grp in grouped:
        # Сливаем инструкции (берём первую)
        instr = grp["Инструкция"].iloc[0]
        # Формируем список словарей [{Ингредиент, Количество, Группа}, ...]
        ing_list = grp[["Ингредиент","Количество","Группа"]].to_dict(orient="records")
        recipes.append({
            "Рецепт": rname,
            "ИнгредиентыJSON": ing_list,  # cохраняем как список
            "Инструкция": instr
        })

    final_df = pd.DataFrame(recipes)
    return final_df

###################################################################
def sum_ingredients(cart_df: pd.DataFrame):
    rows = []
    for _, row in cart_df.iterrows():
        recipe_name = row["Рецепт"]
        portions = row["Порции"]
        ing_list = row["ИнгредиентыJSON"]  # list of dict
        if not isinstance(ing_list, list):
            continue
        for ing_dict in ing_list:
            iname = ing_dict["Ингредиент"]
            grp = ing_dict["Группа"]
            qty_str = ing_dict["Количество"]
            base_q, unit = parse_quantity(qty_str)
            total = base_q * portions
            rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": iname,
                "Группа": grp,
                "Количество_число": total,
                "Единица": unit
            })
    tmp_df = pd.DataFrame(rows)
    if tmp_df.empty:
        return pd.DataFrame()
    grouped = tmp_df.groupby(["Ингредиент", "Группа", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","ИнгредиентыJSON","Инструкция"])

    # Найдём строку в df_parsed
    row_data = df_parsed[df_parsed["Рецепт"] == recipe_name].iloc[0]
    # Проверим, есть ли этот рецепт уже в cart
    cart = st.session_state["cart"]
    existing_index = cart[cart["Рецепт"] == recipe_name].index
    if not existing_index.empty:
        # Прибавим порции
        idx = existing_index[0]
        st.session_state["cart"].loc[idx, "Порции"] += portions
        st.success(f"У рецепта «{recipe_name}» теперь {st.session_state['cart'].loc[idx, 'Порции']} порций!")
    else:
        # Добавляем новую строку
        # row_data["ИнгредиентыJSON"] (list of dict)
        # row_data["Инструкция"]
        new_df = pd.DataFrame([{
            "Рецепт": row_data["Рецепт"],
            "Порции": portions,
            "ИнгредиентыJSON": row_data["ИнгредиентыJSON"],
            "Инструкция": row_data["Инструкция"]
        }])
        st.session_state["cart"] = pd.concat([st.session_state["cart"], new_df], ignore_index=True)
        st.success(f"Добавлен рецепт «{recipe_name}» x {portions} порций!")

def remove_recipe_from_cart(recipe_name):
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        st.write("Нет рецептов!")
        return

    #--- Поиск
    st.header("Поиск по ингредиенту")
    ing_search = st.text_input("Введите название ингредиента:")
    if ing_search:
        # df: Рецепт, ИнгредиентыJSON, Инструкция
        # Надо просканировать каждую JSON
        found_recipes = []
        for _, row in df.iterrows():
            ing_list = row["ИнгредиентыJSON"]
            for d in ing_list:
                if ing_search.lower() in d["Ингредиент"].lower():
                    found_recipes.append(row["Рецепт"])
                    break
        if found_recipes:
            st.subheader("Рецепты с этим ингредиентом:")
            for rcp in found_recipes:
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено рецептов.")
        st.write("---")

    #--- Добавление рецептов
    st.header("Добавить рецепты в список (с учётом порций)")
    rec_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""] + list(rec_list))
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)

    #--- Выбранные рецепты
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"]
        for idx, row_c in cart_df.iterrows():
            rname = row_c["Рецепт"]
            pors = row_c["Порции"]
            st.markdown(f"- **{rname}** (порций: {pors})")
            if st.button(f"Удалить «{rname}»"):
                remove_recipe_from_cart(rname)
                st.success(f"«{rname}» удалён!")
                return
        st.write("---")

        # Итоговый список ингредиентов
        st.write("### Итоговый список ингредиентов (по группам)")
        summed = sum_ingredients(cart_df)
        if not summed.empty:
            group_g = summed.groupby("Группа")
            for grp_name in sorted(group_g.groups.keys()):
                sub_c = group_g.get_group(grp_name)
                st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
                for _, row_s in sub_c.iterrows():
                    iname = row_s["Ингредиент"]
                    num = row_s["Количество_число"]
                    unit = row_s["Единица"]
                    line = f"- **{iname}**: {num} {unit}" if unit else f"- **{iname}**: {num}"
                    st.markdown(line)
        else:
            st.write("Нет ингредиентов.")
        st.write("---")

    #--- Все рецепты (оригинал)
    st.header("Все рецепты (оригинал)")

    for _, row_d in df.iterrows():
        rname = row_d["Рецепт"]
        st.markdown(f"## {rname}")
        st.markdown("**Ингредиенты:**")
        ing_list = row_d["ИнгредиентыJSON"]
        for d in ing_list:
            iname = d["Ингредиент"]
            qty = d["Количество"]
            qpart = f" — {qty}" if qty else ""
            st.markdown(f"- {iname}{qpart}")
        st.markdown(f"**Инструкция:**\n{row_d['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
