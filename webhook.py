from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from pathlib import Path

# Explicitly load the .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
STORE_URL = os.getenv('STORE_URL')

# Debug: Confirm environment variables are loaded
print(f"SHOPIFY_ACCESS_TOKEN: {SHOPIFY_ACCESS_TOKEN}")
print(f"STORE_URL: {STORE_URL}")

@app.route('/', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    if 'id' in data:  # Ensure it's a valid product object
        product = data
        create_or_update_product(product)
    return jsonify({'status': 'success'}), 200

def create_or_update_product(product):
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN
    }

    sku = get_sku_from_product(product)
    if not sku:
        print("Product does not have a SKU, skipping.")
        return

    print(f"Processing product with SKU: {sku}")
    existing_product_id = get_existing_product_id_by_sku(sku, headers)

    if existing_product_id:
        url = f"{STORE_URL}/products/{existing_product_id}.json"
        print(f"Updating product with ID {existing_product_id}")
        response = requests.put(url, json={"product": product}, headers=headers)
    else:
        url = f"{STORE_URL}/products.json"
        print(f"Creating new product with SKU {sku}")
        response = requests.post(url, json={"product": product}, headers=headers)

    if response.status_code in [200, 201]:
        print("Product created/updated successfully:", response.json())
    else:
        print("Error:", response.status_code, response.text)

def get_sku_from_product(product):
    variants = product.get("variants", [])
    if not variants:
        return None
    return variants[0].get("sku")

def get_existing_product_id_by_sku(sku, headers):
    url = f"{STORE_URL}/products.json?fields=id,variants"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        products = response.json().get("products", [])
        for p in products:
            for variant in p.get("variants", []):
                if variant.get("sku") == sku:
                    return p["id"]
    else:
        print("Error fetching products from target store:", response.status_code, response.text)
    return None

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use PORT env var in production
    app.run(host="0.0.0.0", port=port, debug=True)
