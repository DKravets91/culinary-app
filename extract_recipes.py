import fitz  # PyMuPDF
import pandas as pd

# Функция для извлечения текста из PDF
def extract_recipes_from_pdf(pdf_path):
    recipes = []
    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text()
        recipes.append(text)
    doc.close()
    return recipes

# Путь к файлу PDF
pdf_path = 'data/zagotovki_iz_tvoroga.pdf'  # Замени на название своего файла
recipes_text = extract_recipes_from_pdf(pdf_path)

# Сохраним рецепты в CSV
recipes_df = pd.DataFrame({'Рецепт': recipes_text})
recipes_df.to_csv('recipes.csv', index=False)

print("Рецепты успешно извлечены и сохранены в файл recipes.csv!")


