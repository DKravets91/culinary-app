import streamlit as st
import pandas as pd
import re

#########################################################
# СЛОВАРЬ СИНОНИМОВ ДЛЯ УНИФИКАЦИИ
#########################################################
# Если в старом CSV встречаются разные написания одного и того же ингредиента,
# добавляем их сюда. Ключ -> пишем то, что встречается,
# значение -> к чему приводим.
SYNONYMS = {
    "мука пшеничная": "пшеничная мука",
    "пшеничная мука": "пшеничная мука",
    "ваниль по желанию": "ванильная паста",
    # при необходимости дополняем
}

#########################################################
# СЛОВАРЬ ДЛЯ АВТОМАТИЧЕСКИХ КАТЕГОРИЙ
#########################################################
# Ключ -> подстрока, которая, если встречается в названии ингредиента,
#         значит этот ингредиент относится к категории.
# Значение -> текст категории.
AUTO_CATEGORIES = {
    "творог": "Молочные продукты",
    "сливки": "Молочные продукты",
    "сыр": "Сыры",
    "яйц": "Яйца",  # "яйцо", "яйца"
    "мука": "Мука и злаки",
    "крахмал": "Мука и злаки",  # или "Крахмалы", если хочется отдельно
    "укроп": "Овощи и зелень",
    "соль": "Специи и приправы",
    "перец": "Специи и приправы",
    "ваниль": "Специи и приправы",
    "вишн": "Ягоды",
    "шоколад": "Кондитерские изделия",
    "сахар": "Сахар и подсластители",
    # при необходимости расширяем
}


#########################################################
# ФУНКЦИИ
#########################################################
def parse_quantity(qty_str: str):
    """
    Преобразует строку вида '100 г' или '2 шт' в (число, единица).
    Возвращает (0.0, '') если не удалось распарсить.
    """
    match = re.match(r"(\d+)\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка)", qty_str.strip(), re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        return (num, unit.lower())
    return (0.0, "")


def unify_ingredient_name(name: str):
    """
    Убираем лишние пробелы, дефисы и точки в конце.
    Если в словаре SYNONYMS есть такой ключ, приводим к единому названию.
    """
    name = name.strip().lower()
    if name in SYNONYMS:
        name = SYNONYMS[name]
    return name


def auto_assign_category(ing: str):
    """
    Если категория не указана, пытаемся найти её по словарю AUTO_CATEGORIES.
    Поиск делаем по подстроке.
    """
    ing_lower = ing.lower()
    for key_sub, cat_name in AUTO_CATEGORIES.items():
        if key_sub in ing_lower:
            return cat_name
    return ""


@st.cache_data
def load_and_parse(csv_path="recipes.csv"):
    """
    Считываем старый CSV (Рецепт, Ингредиенты, Инструкция)
    и на лету создаём DataFrame: [Рецепт, Ингредиент, Количество, Категория, Инструкция].
    Без отладочного вывода.
    """
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
            # 1) Ищем количество
            quantity_match = re.search(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing, re.IGNORECASE)
            quantity = quantity_match.group(0) if quantity_match else ""

            # 2) Ищем категорию в скобках (если прописана)
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # 3) Очищаем название ингредиента
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (…)
            ing_clean = re.sub(r"(\d+\s?(г|гр|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean, flags=re.IGNORECASE)
            # Убираем дефисы и точки в конце
            ing_clean = re.sub(r"\s?[—-]{1,2}\s?$", "", ing_clean)
            ing_clean = re.sub(r"\s?\.\s?$", "", ing_clean)
            ing_clean = ing_clean.strip()

            # 4) Приводим название к единообразию (через SYNONYMS)
            ing_clean = unify_ingredient_name(ing_clean)

            # 5) Если категория не найдена, пытаемся выставить автоматически
            if not category:
                category = auto_assign_category(ing_clean)

            new_rows.append({
                "Рецепт": recipe_name,
                "Ингредиент": ing_clean,  # уже унифицирован
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    return pd.DataFrame(new_rows)


def sum_ingredients(selected_df):
    """
    Суммируем ингредиенты (числовые).
    """
    parsed_list = []
    for _, row in selected_df.iterrows():
        ing = row["Ингредиент"]
        qty_str = row["Количество"]
        num, unit = parse_quantity(qty_str)
        parsed_list.append({
            "Ингредиент": ing,
            "Количество_число": num,
            "Единица": unit,
        })
    tmp_df = pd.DataFrame(parsed_list)

    # Группируем по [Ингредиент, Единица]
    grouped = tmp_df.groupby(["Ингредиент", "Единица"], as_index=False)["Количество_число"].sum()

    return grouped


def main():
    st.title("Кулинарный помощник 🍳")

    # Загружаем и парсим CSV
    df = load_and_parse("recipes.csv")
    if df.empty:
        return

    # ============ Выбор нескольких рецептов для суммирования ============
    st.header("Выберите несколько рецептов для суммирования:")
    recipes_list = df["Рецепт"].unique().tolist()
    selected = st.multiselect("Выберите рецепты:", recipes_list)

    if selected:
        selected_df = df[df["Рецепт"].isin(selected)]
        # Суммируем
        summed_df = sum_ingredients(selected_df)
        st.write("### Итоговый список ингредиентов:")
        for _, row_sum in summed_df.iterrows():
            ing = row_sum["Ингредиент"]
            num = row_sum["Количество_число"]
            unit = row_sum["Единица"]
            if unit:
                st.markdown(f"- **{ing}**: {num} {unit}")
            else:
                st.markdown(f"- **{ing}**: {num}")
        st.write("---")

    # ============ Вывод всех рецептов, сортировка по категории ============
    st.header("📋 Все рецепты")
    grouped = df.groupby("Рецепт")

    for recipe_name, group in grouped:
        st.markdown(f"## {recipe_name}")
        st.markdown("**Ингредиенты (сгруппированные по категориям):**")

        # Группируем по "Категория"
        cat_grouped = group.groupby("Категория")

        # Перебираем категории в алфавитном порядке
        for cat_name in sorted(cat_grouped.groups.keys()):
            st.write(f"### {cat_name if cat_name else 'Без категории'}")
            sub = cat_grouped.get_group(cat_name)
            for _, row_ing in sub.iterrows():
                ing = row_ing["Ингредиент"]
                qty = row_ing["Количество"]

                # Формируем строку
                qty_part = f" — {qty}" if qty else ""
                st.markdown(f"- {ing}{qty_part}")

        # Инструкция
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
