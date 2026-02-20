import requests

API_URL = "http://localhost:8000/api/v1/products/"

# The Mock Data from your Frontend
PRODUCTS = [
  {"name": "Aashirvaad Shudh Chakki Atta", "category": "Staples", "unit": "10 kg", "mrp": 540, "image_url": "https://m.media-amazon.com/images/I/71rBdK8N5WL._AC_UF1000,1000_QL80_.jpg"},
  {"name": "India Gate Basmati Rice", "category": "Staples", "unit": "5 kg", "mrp": 850, "image_url": "https://m.media-amazon.com/images/I/71W+Q5-v5EL._AC_UF1000,1000_QL80_.jpg"},
  {"name": "Fortune Sunlite Refined Oil", "category": "Oil & Ghee", "unit": "1 L", "mrp": 165, "image_url": "https://m.media-amazon.com/images/I/51+8r6mDkL._SY300_SX300_.jpg"},
  {"name": "Surf Excel Easy Wash", "category": "Cleaning", "unit": "1 kg", "mrp": 145, "image_url": "https://m.media-amazon.com/images/I/61M-J+b+dL._AC_UF1000,1000_QL80_.jpg"},
  {"name": "Cinthol Original Soap", "category": "Personal Care", "unit": "100g x 4", "mrp": 180, "image_url": "https://m.media-amazon.com/images/I/61+9Y3+b+dL._AC_UF1000,1000_QL80_.jpg"},
  {"name": "Maggi Noodles 12-Pack", "category": "Snacks", "unit": "840g", "mrp": 168, "image_url": "https://m.media-amazon.com/images/I/81TopWoq5WL._AC_UF1000,1000_QL80_.jpg"}
]

print("🌱 Seeding Products...")

for p in PRODUCTS:
    try:
        r = requests.post(API_URL, json=p)
        if r.status_code == 200:
            print(f"✅ Added: {p['name']}")
        else:
            print(f"❌ Failed: {p['name']} - {r.text}")
    except Exception as e:
        print(f"Error connecting: {e}")

print("✨ Done!")