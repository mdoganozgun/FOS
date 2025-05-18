import json
from db_config import get_connection

with open("static/data/menu_item_images.json", "r") as f:
    image_map = json.load(f)

conn = get_connection()
cursor = conn.cursor()

for item_name, image_path in image_map.items():
    if image_path.startswith("static/uploads/"):
        image_path = image_path.replace("static/uploads/", "uploads/")
    elif image_path.startswith("static/"):
        image_path = image_path.replace("static/", "")
    cursor.execute("""
        UPDATE MenuItem
        SET image = %s
        WHERE itemName = %s
    """, (image_path, item_name))

conn.commit()
conn.close()
print("✅ MenuItem.image alanları güncellendi.")

# python update_images.py bu kodu terminale yaz.