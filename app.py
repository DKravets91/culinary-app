import streamlit as st
import pandas as pd
import re

######################################################
# СИНОНИМЫ И АВТОГРУППЫ
######################################################
SYNONYMS = {
    "мука пшеничная": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",
    # При необходимости дополняйте
}

AUTO_GROUPS = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",         # «Яйца (категория c1)» => всё равно «яйца»
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
    "для начинки": "",     # пропускаем целиком
}

######################################################
# parse_quantity : "100 г" -> (100, "г")
######################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

######################################################
# unify_ingredient_name : приведение к нижнему регистру, синонимы
######################################################
def unify_ingredient_name(name: str) -> str:
    name = name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

######################################################
# auto_assign_group : поиск в словаре AUTO_GROUPS
######################################################
def auto_assign_group(ing_name: str) -> str:
    ing_lower = ing_name.lower()
    for key_sub, group in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group
    return ""

######################################################
# load_and_parse : загружаем CSV (3 колонки),
#   parse по строкам ингредиентов (разделённых \n),
#   sливаем ингредиенты в список JSON
#   (recipe -> 1 строка).
######################################################
@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    df_raw = pd.read_csv(csv_path)
    df_raw.columns = df_raw.columns.str.strip()

    needed = {"Рецепт", "Ингредиенты", "Инструкция"}
    missing = needed - set(df_raw.columns)
    if missing:
        st.error(f"Не найдены столбцы: {missing}")
        return pd.DataFrame()

    parse_rows = []
    for _, row in df_raw.iterrows():
        recipe_name = str(row["Рецепт"]).strip()
        instruction = str(row["Инструкция"]).strip()
        lines = str(row["Ингредиенты"]).split("\n")

        for ing_line in lines:
            ing_line = ing_line.strip()
            if not ing_line or "для начинки" in ing_line.lower():
                continue

            # Ищем "100 г", "2 шт." и т.п.
            qty_match = re.search(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing_line, re.IGNORECASE)
            quantity = qty_match.group(0).strip() if qty_match else ""

            # group (скобки) НЕ вытаскиваем как категорию,
            # всё автоподбираем через auto_assign_group
            # Но если user хочет «(категория c1)» оставить в названии, оставим:
            # Уберём только числовые части
            name_no_qty = re.sub(r"(\d+.*?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_line, flags=re.IGNORECASE)

            # Убираем возможные «--» и точки
            name_no_qty = re.sub(r"\s?[—-]{1,2}\s?$", "", name_no_qty)
            name_no_qty = re.sub(r"\s?\.\s?$", "", name_no_qty)
            name_no_qty = name_no_qty.strip()

            # unify_ingredient_name
            ing_clean = unify_ingredient_name(name_no_qty)

            # auto_assign_group
            grp = auto_assign_group(ing_clean)

            parse_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": name_no_qty.strip(),  # Оригинал (нижний регистр?),
                "Количество": quantity.strip(),
                "Группа": grp,
                "Инструкция": instruction
            })

    if not parse_rows:
        return pd.DataFrame()

    df_parsed = pd.DataFrame(parse_rows)

    # Сгруппируем : 1 рецепт => 1 строка.
    # ingredients => list of dict
    final_recipes = []
    grouped = df_parsed.groupby("Рецепт")
    for rcp, subdf in grouped:
        instruct = subdf["Инструкция"].iloc[0]
        ing_list = subdf[["Ингредиент","Количество","Группа"]].to_dict(orient="records")
        final_recipes.append({
            "Рецепт": rcp,
            "ИнгредиентыJSON": ing_list,
            "Инструкция": instruct
        })
    return pd.DataFrame(final_recipes)

######################################################
# sum_ingredients : перебираем корзину, умножаем qty * порции
######################################################
def sum_ingredients(cart_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c_row in cart_df.iterrows():
        recipe_name = c_row["Рецепт"]
        portions = c_row["Порции"]
        ing_list = c_row["ИнгредиентыJSON"]
        if not isinstance(ing_list, list):
            continue
        for ing_item in ing_list:
            iname = ing_item["Ингредиент"]
            grp = ing_item["Группа"]
            qty_str = ing_item["Количество"]
            base, unit = parse_quantity(qty_str)
            total = base * portions
            rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": iname,
                "Группа": grp,
                "Количество_число": total,
                "Единица": unit
            })
    if not rows:
        return pd.DataFrame()
    sumdf = pd.DataFrame(rows)
    result = sumdf.groupby(["Ингредиент","Группа","Единица"], as_index=False)["Количество_число"].sum()
    return result

######################################################
# Добавляем рецепт
######################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт","Порции","ИнгредиентыJSON","Инструкция"])

    # Найдём строку в df_parsed
    row_df = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if row_df.empty:
        st.error("Рецепт не найден.")
        return
    # Берём первую строку
    row = row_df.iloc[0]

    cart = st.session_state["cart"]
    exist_idx = cart[cart["Рецепт"] == recipe_name].index
    if len(exist_idx) > 0:
        # Уже есть => увеличиваем "Порции"
        idx = exist_idx[0]
        old_pors = cart.loc[idx, "Порции"]
        new_pors = old_pors + portions
        st.session_state["cart"].loc[idx, "Порции"] = new_pors
        st.success(f"У «{recipe_name}» теперь {new_pors} порций!")
    else:
        # Добавляем новую запись
        new_df = pd.DataFrame([{
            "Рецепт": row["Рецепт"],
            "Порции": portions,
            "ИнгредиентыJSON": row["ИнгредиентыJSON"],
            "Инструкция": row["Инструкция"]
        }])
        st.session_state["cart"] = pd.concat([st.session_state["cart"], new_df], ignore_index=True)
        st.success(f"Добавлен «{recipe_name}» x {portions} порций!")

def remove_recipe_from_cart(recipe_name):
    if "cart" not in st.session_state:
        return
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

######################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        st.write("Нет рецептов для загрузки.")
        return

    #=== Поиск
    st.header("Поиск по ингредиенту")
    ing_sea = st.text_input("Введите название ингредиента:")
    if ing_sea:
        found = []
        for _, r in df.iterrows():
            ings = r["ИнгредиентыJSON"]
            if isinstance(ings, list):
                for iitem in ings:
                    if ing_sea.lower() in iitem["Ингредиент"].lower():
                        found.append(r["Рецепт"])
                        break
        if found:
            st.subheader("Рецепты, где есть этот ингредиент:")
            for rc in found:
                st.markdown(f"- **{rc}**")
        else:
            st.write("Не найдено.")
        st.write("---")

    #=== Добавление рецептов
    st.header("Добавить рецепты в список (с учётом порций)")
    recipe_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", [""] + list(recipe_list))
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)
    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)

    #=== Выбранные рецепты
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        cart_df = st.session_state["cart"]
        for iidx, c_row in cart_df.iterrows():
            rcp = c_row["Рецепт"]
            pors = c_row["Порции"]
            st.markdown(f"- **{rcp}** (порций: {pors})")
            # Кнопка удалить
            if st.button(f"Удалить «{rcp}»"):
                remove_recipe_from_cart(rcp)
                st.success(f"«{rcp}» удалён!")
                return
        st.write("---")

        # Итого ингредиенты
        st.write("### Итоговый список ингредиентов (по группам)")
        summ = sum_ingredients(cart_df)
        if not summ.empty:
            grouped = summ.groupby("Группа")
            for grp_name in sorted(grouped.groups.keys()):
                sub_c = grouped.get_group(grp_name)
                st.markdown(f"#### {grp_name if grp_name else 'Без группы'}")
                for _, srow in sub_c.iterrows():
                    iname = srow["Ингредиент"]
                    num = srow["Количество_число"]
                    unit = srow["Единица"]
                    line = f"- **{iname}**: {num} {unit}" if unit else f"- **{iname}**: {num}"
                    st.markdown(line)
        else:
            st.write("Нет ингредиентов.")
        st.write("---")

    #=== Все рецепты (оригинал)
    st.header("Все рецепты (оригинал)")
    for _, rowx in df.iterrows():
        rcpn = rowx["Рецепт"]
        st.markdown(f"## {rcpn}")
        st.markdown("**Ингредиенты:**")
        ings = rowx["ИнгредиентыJSON"]
        if isinstance(ings, list):
            for d in ings:
                ingname = d["Ингредиент"]
                qty = d["Количество"]
                sgrp = d["Группа"]
                qpart = f" — {qty}" if qty else ""
                st.markdown(f"- {ingname}{qpart}")
        st.markdown(f"**Инструкция:**\n{rowx['Инструкция']}")
        st.write("---")

if __name__ == "__main__":
    main()
