import streamlit as st
import pandas as pd
import re


@st.cache_data
def load_and_transform_data(csv_path):
    """
    Считываем старый recipes.csv со столбцами:
      - Название
      - Ингредиенты
      - Инструкция
    И преобразуем в DataFrame со столбцами:
      - Рецепт
      - Ингредиент
      - Количество
      - Категория
      - Инструкция
    """
    df_old = pd.read_csv(csv_path)
    df_old.columns = df_old.columns.str.strip()  # убираем пробелы в названиях

    # Проверка, что столбцы есть
    needed_cols = {"Название", "Ингредиенты", "Инструкция"}
    if not needed_cols.issubset(df_old.columns):
        st.error("В старом файле нет необходимых столбцов: "
                 f"{needed_cols - set(df_old.columns)}")
        return pd.DataFrame()

    # Разбиваем ингредиенты по строкам
    # Предположим, каждый рецепт может иметь несколько ингредиентов в поле 'Ингредиенты'
    # разделённых символом новой строки '\n' (или ';', если так хранили).
    new_rows = []

    for _, row in df_old.iterrows():
        recipe_name = row["Название"]
        instruction = row["Инструкция"]

        # Разделяем строку ингредиентов
        ingredients_list = row["Ингредиенты"].split("\n")  # или split(";")

        for ing in ingredients_list:
            # Извлечение количества и категории из строки
            quantity_match = re.search(r"(\d+\s?(г|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", ing)
            quantity = quantity_match.group(0) if quantity_match else ""

            # Извлекаем категорию из круглых скобок, если есть
            category_match = re.search(r"\((.*?)\)", ing)
            category = category_match.group(1) if category_match else ""

            # Очищаем название ингредиента от количества и категории
            ing_clean = re.sub(r"\(.*?\)", "", ing)  # убираем (... )
            ing_clean = re.sub(r"(\d+\s?(г|мл|шт|kg|л|ст\.л|ч\.л|щепотка))", "", ing_clean)
            ing_clean = ing_clean.strip(" -")

            new_rows.append({
                "Рецепт": recipe_name.strip(),
                "Ингредиент": ing_clean.strip(),
                "Количество": quantity.strip(),
                "Категория": category.strip(),
                "Инструкция": instruction
            })

    df_new = pd.DataFrame(new_rows)
    return df_new


def main():
    st.title("Кулинарный помощник 🍳 (преобразование старого CSV)")

    # Загружаем старый CSV и преобразуем "на лету"
    df = load_and_transform_data("recipes.csv")  # укажи правильный путь

    # Если DataFrame пуст — завершаем
    if df.empty:
        return

    st.write("Преобразованный DataFrame:", df.head(10))

    # -- Ниже можно использовать df, как будто у нас столбцы
    #    Рецепт, Ингредиент, Количество, Категория, Инструкция

    st.header("🔍 Поиск рецептов по ингредиенту")
    ingredient_search = st.text_input("Введите ингредиент для поиска:")
    if ingredient_search:
        filtered = df[df["Ингредиент"].str.contains(ingredient_search, case=False, na=False)]
        if not filtered.empty:
            st.subheader("🍽️ Найденные рецепты:")
            grouped = filtered.groupby("Рецепт")
            for recipe_name, group in grouped:
                st.markdown(f"## {recipe_name}")
                st.markdown("**Ингредиенты:**")
                for _, row in group.iterrows():
                    st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
                st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        else:
            st.write("😔 Рецепты с этим ингредиентом не найдены.")

    st.header("📋 Все рецепты")
    all_grouped = df.groupby("Рецепт")
    for recipe_name, group in all_grouped:
        st.markdown(f"### {recipe_name}")
        st.markdown("**Ингредиенты:**")
        for _, row in group.iterrows():
            st.markdown(f"- {row['Ингредиент']} — {row['Количество']} ({row['Категория']})")
        st.markdown(f"**Инструкция:**\n{group.iloc[0]['Инструкция']}")
        st.write("---")


if __name__ == "__main__":
    main()
