import streamlit as st
import pandas as pd
import re

###########################################################
# СИНОНИМЫ И АВТОГРУППЫ
###########################################################
SYNONYMS = {
    # Можем использовать для других ингредиентов, пока не трогаем яйца (категория c1)
    "мука пшеничная": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    "микс сушёных трав": "микс сушёных трав",
    # Если захотите объединять "Яйцо куриное" -> "Яйца (категория С1)", добавьте
}

AUTO_GROUPS = {
    "творог": "молочные продукты",
    "сливки": "молочные продукты",
    "сыр": "молочные продукты",
    "сулугуни": "молочные продукты",
    "молоко": "молочные продукты",
    "масло": "молочные продукты",
    "яйц": "яйца",    # Если в названии есть "яйц", ставим группу "яйца"
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

###########################################################
# Парсинг количества: "100 г" -> (100, "г")
###########################################################
def parse_quantity(qty_str: str):
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        return (num, unit)
    return (0.0, "")

###########################################################
# Унификация названия ингредиента (кроме "яйца (категория С1)")
###########################################################
def unify_ingredient_name(original_name: str):
    """
    Если хотите, чтобы 'яйцо куриное' становилось 'Яйца (категория С1)', можете сделать это здесь.
    Но сейчас оставим оригинальный текст для яиц, не трогаем '(категория c1)'.
    """
    name = original_name.strip().lower()
    # Применим словарь SYNONYMS
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name.strip()

###########################################################
# Автоматическое определение группы (столбец "Группа")
###########################################################
def auto_assign_group(ing: str) -> str:
    ing_lower = ing.lower()
    for key_sub, group_name in AUTO_GROUPS.items():
        if key_sub in ing_lower:
            return group_name
    return ""

###########################################################
# Загрузка и парсинг CSV (3 колонки -> 5 колонки)
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
                # Пропускаем пустые или «для начинки»
                continue

            # Выделим количество
            qty_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = qty_match.group(0) if qty_match else ""

            # Группа из скобок? (для яиц (категория C1) не будем ломать)
            group_match = re.search(r"\((.*?)\)", ing)
            group_str = group_match.group(1) if group_match else ""

            # Очистим название (уберём количество, но оставим '(категория c1)' если оно есть)
            # Или, если хотите убирать '(категория c1)' — раскомментируйте
            # ing_clean = re.sub(r"\(.*?\)", "", ing, flags=re.IGNORECASE)
            # Но вы сказали "Яйца (категория С1)" — пусть остаётся
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing, flags=re.IGNORECASE)
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            ing_clean = unify_ingredient_name(ing_clean)

            # Если group_str не задана, делаем auto_assign
            if not group_str:
                group_str = auto_assign_group(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,    # Сохраняем "Яйца (категория С1)" если так было
                "Количество": quantity.strip(),
                "Группа": group_str.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)

###########################################################
# Суммируем ингредиенты (учитывая "Группа")
###########################################################
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
    # Группируем (Ингредиент, Группа, Единица)
    grouped = tmp_df.groupby(["Ингредиент", "Группа", "Единица"], as_index=False)["Количество_число"].sum()
    return grouped

###########################################################
# Добавление рецепта в корзину + поле "Порции"
###########################################################
def add_recipe_to_cart(recipe_name, portions, df_parsed):
    if "cart" not in st.session_state:
        st.session_state["cart"] = pd.DataFrame(columns=["Рецепт", "Порции", "Ингредиент", "Количество", "Группа", "Инструкция"])

    selected_rows = df_parsed[df_parsed["Рецепт"] == recipe_name]
    if selected_rows.empty:
        return

    # Добавляем столбец "Порции" к каждой строке
    extended = selected_rows.copy()
    extended["Порции"] = portions

    # Складываем
    st.session_state["cart"] = pd.concat([st.session_state["cart"], extended], ignore_index=True)

def remove_recipe_from_cart(recipe_name):
    """Удаляем строки, относящиеся к этому рецепту"""
    if "cart" not in st.session_state:
        return
    # Удаляем по названию
    st.session_state["cart"] = st.session_state["cart"][st.session_state["cart"]["Рецепт"] != recipe_name]

###########################################################
def main():
    st.title("Кулинарный помощник 🍳")

    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    ###################################################################
    # Поиск по ингредиенту
    ###################################################################
    st.header("Поиск по ингредиенту")
    ingredient_search = st.text_input("Введите название ингредиента:")
    if ingredient_search:
        # Фильтруем по нижнему регистру
        filtered = df[df["Ингредиент"].str.contains(ingredient_search.lower(), case=False, na=False)]
        if not filtered.empty:
            st.subheader("Рецепты, где встречается этот ингредиент:")
            for rcp in filtered["Рецепт"].unique():
                st.markdown(f"- **{rcp}**")
        else:
            st.write("Не найдено рецептов с таким ингредиентом.")
        st.write("---")

    ###################################################################
    # Добавление рецептов с порциями
    ###################################################################
    st.header("Добавить рецепты в список (с учётом порций)")
    recipes_list = df["Рецепт"].unique().tolist()
    recipe_choice = st.selectbox("Выберите рецепт:", ["" ]+ recipes_list)
    portions = st.number_input("Количество порций:", min_value=1, max_value=50, value=1)

    if st.button("Добавить в список"):
        if recipe_choice:
            add_recipe_to_cart(recipe_choice, portions, df)
            st.success(f"Добавлен рецепт: {recipe_choice} x {portions} порций!")

    ###################################################################
    # Отображение выбранных рецептов, возможность удаления
    ###################################################################
    st.header("Выбранные рецепты (список)")
    if "cart" not in st.session_state or st.session_state["cart"].empty:
        st.write("Пока нет добавленных рецептов.")
    else:
        # Покажем таблицу с выбором
        cart_df = st.session_state["cart"]
        # Группируем по названию рецепта, выводим суммарные порции
        grouped_recipes = cart_df.groupby("Рецепт")["Порции"].sum().reset_index()
        for idx, row_r in grouped_recipes.iterrows():
            rec_name = row_r["Рецепт"]
            total_portions = row_r["Порции"]
            st.markdown(f"- **{rec_name}** (всего порций: {total_portions})")
            # Кнопка удалить
            if st.button(f"Удалить «{rec_name}»"):
                remove_recipe_from_cart(rec_name)
                # Не используем rerun, чтоб не падала ошибка. Перезапуск вручную.
                st.success(f"«{rec_name}» удалён!")
                return  # выйдем из main(), при следующем рендере обновится

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

    ###################################################################
    # Все рецепты (оригинал)
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
