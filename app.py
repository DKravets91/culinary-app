import streamlit as st
import pandas as pd
import re

################################################################
# СИНОНИМЫ И АВТОГРУППЫ
################################################################
SYNONYMS = {
    "мука пшеничная": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",
    # Дополните при необходимости
}

AUTO_GROUPS = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",         # «Яйца (категория c1)» => "яйца"
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

################################################################
# parse_quantity : "100 г" -> (100.0, "г")
################################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

################################################################
# unify_ingredient_name
################################################################
def unify_ingredient_name(ing: str) -> str:
    ing = ing.strip().lower()
    if ing in SYNONYMS:
        ing = SYNONYMS[ing]
    return ing.strip()

################################################################
# auto_assign_group
################################################################
def auto_assign_group(ing: str) -> str:
    ing_lower = ing.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

################################################################
# load_and_parse : CSV (3 cols) -> dataframe (1 row = 1 recipe + JSON ingredients)
################################################################
@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()

    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_old.columns)
    if missing:
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    # Разбиваем на построчные ингредиенты
    parse_rows = []
    for _, row in df_old.iterrows():
        recipe_name = row["Рецепт"].strip()
        instruction = row["Инструкция"]
        ing_lines = str(row["Ингредиенты"]).split("\n")
        for line in ing_lines:
            line = line.strip()
            if not line or "для начинки" in line.lower():
                continue

            # Количество
            qty_match = re.search(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", line, re.IGNORECASE)
            quantity = qty_match.group(0).strip() if qty_match else ""

            # Убираем numeric из названия, не удаляем (категория c1)
            name_no_qty = re.sub(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", line, flags=re.IGNORECASE)
            # Убираем лишние тире, точки
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            # unify / auto group
            ing_clean = unify_ingredient_name(name_no_qty)
            grp = auto_assign_group(ing_clean)

            parse_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty,   # Оригинал
                "Количество": quantity,
                "Группа": grp,
                "Инструкция": instruction
            })

    if not parse_rows:
        return pd.DataFrame()

    # Группируем post-parse -> 1 строка на рецепт
    df_parsed = pd.DataFrame(parse_rows)
    final_list = []
    grouped = df_parsed.groupby("Рецепт")
    for rcp, sub in grouped:
        instruct = sub["Инструкция"].iloc[0]
        ing_list = sub[["Ингредиент","Количество","Группа"]].to_dict(orient="records")
        final_list.append({
            "Рецепт": rcp,
            "ИнгредиентыJSON": ing_list,
            "Инструкция": instruct
        })

    return pd.DataFrame(final_list)

################################################################
# sum_ingredients : берём cart, умножаем qty * Порции
################################################################
def sum_ingredients(cart_df: pd.DataFrame):
    rows = []
    for _, c_row in cart_df.iterrows():
        rcp = c_row["Рецепт"]
        pors = c_row["Порции"]
        ing_list = c_row["ИнгредиентыJSON"]
        if not isinstance(ing_list, list):
            continue

        for item in ing_list:
            iname = item["Ингредиент"]
            grp = item["Группа"]
            qty_str = item["Количество"]
            base, unit = parse_quantity(qty_str)
            total = base * pors  # <-- умножаем
            rows.append({
                "Рецепт": rcp,
                "Ингредиент": iname,
                "Группа": grp,
                "Количество_число": total,
                "Единица": unit
            })
    if not rows:
        return pd.DataFrame()
    outdf = pd.DataFrame(rows)
    # Группируем, если нужно объединить одинаковые ингредиенты
    outdf = outdf.groupby(["Ингредиент","Группа","Единица"], as_index=False)["Количество_число"].sum()
    return outdf

################################################################
# add_recipe_to_cart
################################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","ИнгредиентыJSON","Инструкция"])

    # Ищем рецепт в df_parsed
    row_df = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if row_df.empty:
        st.error("Рецепт не найден!")
        return
    row = row_df.iloc[0]

    # Проверяем, есть ли уже
    cart = st.session_state["cart"]
    exist_idx = cart[cart["Рецепт"] == recipe_name].index
    if len(exist_idx) > 0:
        # уже есть -> увеличим
        idx = exist_idx[0]
        old_pors = cart.loc[idx, "Порции"]
        new_pors = old_pors + portions
        st.session_state["cart"].loc[idx, "Порции"] = new_pors
        st.success(f"У «{recipe_name}» теперь {new_pors} порций!")
    else:
        # добавляем
        new_df = pd.DataFrame([{
            "Рецепт": row["Рецепт"],
            "Порции": portions,
            "ИнгредиентыJSON": row["ИнгредиентыJSON"],
            "Инструкция": row["Инструкция"]
        }])
        st.session_state["cart"] = pd.concat([st.session_state["cart"], new_df], ignore_index=True)
        st.success(f"Добавлен рецепт «{recipe_name}» x {portions} порций!")

def remove_recipe_from_cart(recipe_name):
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

################################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        st.write("Нет рецептов!")
        return

    #=== Поиск по ингредиенту
    st.header("Поиск по ингредиенту")
    ing_s = st.text_input("Введите ингредиент:")
    if ing_s:
        found = []
        for _, rowx in df.iterrows():
            ings = rowx["ИнгредиентыJSON"]
            if not isinstance(ings, list):
                continue
            for item in ings:
                if ing_s.lower() in item["Ингредиент"].lower():
                    found.append(rowx["Рецепт"])
                    break
        if found:
            st.subheader("Рецепты, где есть такой ингредиент:")
            for rc in found:
                st.markdown(f"- **{rc}**")
        else:
            st.write("Не найдено.")
        st.write("---")

    #=== Добавление рецептов
    st.header("Добавить рецепты (с учётом порций)")
    rec_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""]+list(rec_list))
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

        # Итоговый список
        st.write("### Итоговый список ингредиентов (по группам)")
        summ = sum_ingredients(cart_df)
        if not summ.empty:
            group_g = summ.groupby("Группа")
            for grp_name in sorted(group_g.groups.keys()):
                subcat = group_g.get_group(grp_name)
                st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
                for _, r2 in subcat.iterrows():
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
    for _, rrow in df.iterrows():
        rnm = rrow["Рецепт"]
        st.markdown(f"## {rnm}")
        st.markdown("**Ингредиенты:**")
        ings = rrow["ИнгредиентыJSON"]
        if isinstance(ings, list):
            for item in ings:
                name_i = item["Ингредиент"]
                qty_i = item["Количество"]
                qpart = f" — {qty_i}" if qty_i else ""
                st.markdown(f"- {name_i}{qpart}")
        st.markdown(f"**Инструкция:**\n{rrow['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
