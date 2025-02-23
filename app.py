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
    "яйц": "яйца",   # «(категория c1)» => всё равно «яйца»
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

    parse_rows = []
    for _, row in df_old.iterrows():
        recipe_name = row["Рецепт"].strip()
        instruction = row["Инструкция"]
        lines = str(row["Ингредиенты"]).split("\n")
        for ing_line in lines:
            ing_line = ing_line.strip()
            if not ing_line or "для начинки" in ing_line.lower():
                continue

            # Ищем кол-во (например, "100 г")
            qty_match = re.search(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing_line, re.IGNORECASE)
            quantity = qty_match.group(0).strip() if qty_match else ""

            # Убираем количество (но оставляем "(категория c1)")
            name_no_qty = re.sub(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_line, flags=re.IGNORECASE)
            # Убираем тире, точки
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            ing_clean = unify_ingredient_name(name_no_qty)
            group_str = auto_assign_group(ing_clean)

            parse_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty,   # оригинал (включая "(категория c1)")
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    if not parse_rows:
        return pd.DataFrame()

    df_parsed = pd.DataFrame(parse_rows)

    # Сольём строки одного рецепта в один JSON
    final = []
    for recipe_name, grp in df_parsed.groupby("Рецепт"):
        instruct = grp["Инструкция"].iloc[0]
        # Собираем список словарей {Ингредиент, Количество, Группа}
        ing_list = grp[["Ингредиент","Количество","Группа"]].to_dict(orient="records")
        final.append({
            "Рецепт": recipe_name,
            "ИнгредиентыJSON": ing_list,
            "Инструкция": instruct
        })
    return pd.DataFrame(final)

def sum_ingredients(cart_df: pd.DataFrame):
    rows = []
    for _, c_row in cart_df.iterrows():
        rcp_name = c_row["Рецепт"]
        pors = c_row["Порции"]
        ing_list = c_row["ИнгредиентыJSON"]
        if not isinstance(ing_list, list):
            continue
        for ing_item in ing_list:
            ingname = ing_item["Ингредиент"]
            grp = ing_item["Группа"]
            qty_str = ing_item["Количество"]
            base, unit = parse_quantity(qty_str)
            total = base * pors
            rows.append({
                "Рецепт": rcp_name,
                "Ингредиент": ingname,
                "Группа": grp,
                "Количество_число": total,
                "Единица": unit
            })
    if not rows:
        return pd.DataFrame()
    out_df = pd.DataFrame(rows)
    # Суммируем одинаковые ингредиенты
    out_df = out_df.groupby(["Ингредиент","Группа","Единица"], as_index=False)["Количество_число"].sum()
    return out_df

def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        # столбцы = Рецепт, Порции, ИнгредиентыJSON, Инструкция
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","ИнгредиентыJSON","Инструкция"])

    found_row = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if found_row.empty:
        st.error("Рецепт не найден!")
        return
    row = found_row.iloc[0]

    cart = st.session_state["cart"]
    exist_idx = cart[cart["Рецепт"] == recipe_name].index
    if len(exist_idx) > 0:
        # уже есть -> увеличиваем
        idx = exist_idx[0]
        old_p = cart.loc[idx, "Порции"]
        new_p = old_p + portions
        st.session_state["cart"].loc[idx, "Порции"] = new_p
        st.success(f"У «{recipe_name}» теперь {new_p} порций!")
    else:
        # добавляем
        new_row = pd.DataFrame([{
            "Рецепт": row["Рецепт"],
            "Порции": portions,
            "ИнгредиентыJSON": row["ИнгредиентыJSON"],
            "Инструкция": row["Инструкция"]
        }])
        st.session_state["cart"] = pd.concat([st.session_state["cart"], new_row], ignore_index=True)
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

    #=== Поиск по ингредиенту
    st.header("Поиск по ингредиенту")
    ing_search = st.text_input("Введите название ингредиента:")
    if ing_search:
        found_recs = []
        for _, rowx in df.iterrows():
            ing_list = rowx["ИнгредиентыJSON"]
            for item in ing_list:
                if ing_search.lower() in item["Ингредиент"].lower():
                    found_recs.append(rowx["Рецепт"])
                    break
        if found_recs:
            st.subheader("Рецепты, где есть этот ингредиент:")
            for recp in found_recs:
                st.markdown(f"- **{recp}**")
        else:
            st.write("Не найдено.")
        st.write("---")

    #=== Добавление рецептов
    st.header("Добавить рецепты (с учётом порций)")
    recipe_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""]+list(recipe_list))
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)

    #=== Список выбранных
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"]
        for idx, crow in cart_df.iterrows():
            rname = crow["Рецепт"]
            pors = crow["Порции"]
            st.markdown(f"- **{rname}** (порций: {pors})")
            if st.button(f"Удалить «{rname}»"):
                remove_recipe_from_cart(rname)
                st.success(f"«{rname}» удалён!")
                return

        st.write("---")

        # Итоговый список ингредиентов
        st.write("### Итоговый список ингредиентов (по группам)")
        result_df = sum_ingredients(cart_df)
        if not result_df.empty:
            grouped = result_df.groupby("Группа")
            for grp_name in sorted(grouped.groups.keys()):
                sub_df = grouped.get_group(grp_name)
                st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
                for _, r2 in sub_df.iterrows():
                    iname = r2["Ингредиент"]
                    num = r2["Количество_число"]
                    unit = r2["Единица"]
                    line = f"- **{iname}**: {num} {unit}" if unit else f"- **{iname}**: {num}"
                    st.markdown(line)
        else:
            st.write("Нет ингредиентов.")
        st.write("---")

    #=== Все рецепты (оригинал)
    st.header("Все рецепты (оригинал)")

    for _, rowy in df.iterrows():
        rname = rowy["Рецепт"]
        st.markdown(f"## {rname}")
        st.markdown("**Ингредиенты:**")
        ing_list = rowy["ИнгредиентыJSON"]
        for item in ing_list:
            nm = item["Ингредиент"]
            qty = item["Количество"]
            qpart = f" — {qty}" if qty else ""
            st.markdown(f"- {nm}{qpart}")
        st.markdown(f"**Инструкция:**\n{rowy['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
