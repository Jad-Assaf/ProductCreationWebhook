from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from pathlib import Path

# Explicitly load the .env from the current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# Your other store's API key, password, and store URL
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
STORE_URL = os.getenv('STORE_URL')

# Debug prints to verify environment is loaded
print(f"API_KEY is: {repr(SHOPIFY_ACCESS_TOKEN)}")
print(f"STORE_URL is: {repr(STORE_URL)}")

@app.route('/', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle incoming webhook from Shopify when a product is created or updated.
    """
    data = request.json
    if 'id' in data:  # Ensure it's a valid product object
        product = data
        create_or_update_product(product)
    return jsonify({'status': 'success'}), 200

def create_or_update_product(product):
    """
    Create or update a product in the target store based on its SKU.
    """
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN
    }

    # Extract SKU from the product
    sku = get_sku_from_product(product)
    if not sku:
        print("Product does not have a SKU, skipping.")
        return

    print(f"Processing product with SKU: {sku}")

    # Check if a product with the same SKU exists in the target store
    existing_product_id = get_existing_product_id_by_sku(sku, headers)

    if existing_product_id:
        # Update the existing product
        url = f"{STORE_URL}/products/{existing_product_id}.json"
        print(f"Updating product with ID {existing_product_id}")
        response = requests.put(url, json={"product": product}, headers=headers)
    else:
        # Create a new product
        url = f"{STORE_URL}/products.json"
        print(f"Creating new product with SKU {sku}")
        response = requests.post(url, json={"product": product}, headers=headers)

    # Log the response
    if response.status_code in [200, 201]:
        print("Product created/updated successfully:", response.json())
    else:
        print("Error:", response.status_code, response.text)

def get_sku_from_product(product):
    """
    Extract SKU from the product's variants.
    """
    variants = product.get("variants", [])
    if variants:
        return variants[0].get("sku")  # Assuming the first variant's SKU is used
    return None

def get_existing_product_id_by_sku(sku, headers):
    """
    Check if a product with the given SKU exists in the target store.
    Returns the product ID if found, otherwise None.
    """
    url = f"{STORE_URL}/products.json?fields=id,variants"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        products = response.json().get("products", [])
        for p in products:
            for variant in p.get("variants", []):
                if variant.get("sku") == sku:
                    return p["id"]  # Return the product ID
    else:
        print("Error fetching products from target store:", response.status_code, response.text)
    return None

if __name__ == '__main__':
    app.run(port=5000, debug=True)
