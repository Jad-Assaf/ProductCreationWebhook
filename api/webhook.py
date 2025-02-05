from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
import hmac
import hashlib
import base64
import logging
from pathlib import Path

# Explicitly load environment variables (useful for local development)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Fetch environment variables
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
STORE_URL = os.getenv('STORE_URL')
SHOPIFY_WEBHOOK_SECRET = os.getenv('SHOPIFY_WEBHOOK_SECRET')

# Ensure required environment variables are loaded
if not SHOPIFY_ACCESS_TOKEN or not STORE_URL or not SHOPIFY_WEBHOOK_SECRET:
    raise ValueError("Missing SHOPIFY_ACCESS_TOKEN, STORE_URL, or SHOPIFY_WEBHOOK_SECRET in environment variables.")

def verify_webhook(data, hmac_header):
    """
    Verify the webhook by computing the HMAC digest and comparing it to the header.
    """
    computed_hmac = base64.b64encode(
        hmac.new(SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
                 data,
                 hashlib.sha256).digest()
    ).decode('utf-8')
    return hmac.compare_digest(computed_hmac, hmac_header)

@app.route('/', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle incoming webhook from Shopify when a product is created or updated.
    Verifies the webhook, validates the payload, and processes the product.
    """
    data = request.get_data()  # raw bytes used for HMAC verification
    hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
    if not hmac_header:
        logging.error("Missing HMAC header in the request.")
        return jsonify({'status': 'failure', 'message': 'Missing HMAC header'}), 400

    if not verify_webhook(data, hmac_header):
        logging.error("Webhook verification failed.")
        return jsonify({'status': 'failure', 'message': 'Webhook verification failed'}), 401

    json_data = request.get_json()
    if not json_data or 'id' not in json_data:
        logging.error("Invalid product data received.")
        return jsonify({'status': 'failure', 'message': 'Invalid product data'}), 400

    try:
        create_or_update_product(json_data)
    except Exception as e:
        logging.exception("Error processing the product:")
        return jsonify({'status': 'failure', 'message': str(e)}), 500

    return jsonify({'status': 'success'}), 200

def create_or_update_product(product):
    """
    Create or update a product in the target store based on its SKU.
    """
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN
    }

    sku = get_sku_from_product(product)
    if not sku:
        logging.info("Product does not have a SKU; skipping processing.")
        return

    logging.info(f"Processing product with SKU: {sku}")

    existing_product_id = get_existing_product_id_by_sku(sku, headers)

    try:
        if existing_product_id:
            # Update the existing product
            url = f"{STORE_URL}/products/{existing_product_id}.json"
            logging.info(f"Updating product with ID {existing_product_id}")
            response = requests.put(url, json={"product": product}, headers=headers)
        else:
            # Create a new product
            url = f"{STORE_URL}/products.json"
            logging.info(f"Creating new product with SKU {sku}")
            response = requests.post(url, json={"product": product}, headers=headers)
    except requests.exceptions.RequestException as e:
        logging.exception("HTTP request to the target store failed.")
        raise Exception("HTTP request failed") from e

    if response.status_code in [200, 201]:
        logging.info("Product created/updated successfully: %s", response.json())
    else:
        logging.error("Error from target store: %s %s", response.status_code, response.text)
        raise Exception(f"Error from target store: {response.status_code} {response.text}")

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
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        logging.exception("Failed to fetch products from the target store.")
        raise Exception("Failed to fetch products") from e

    if response.status_code == 200:
        products = response.json().get("products", [])
        for p in products:
            for variant in p.get("variants", []):
                if variant.get("sku") == sku:
                    return p["id"]
    else:
        logging.error("Error fetching products: %s %s", response.status_code, response.text)
        raise Exception(f"Error fetching products: {response.status_code}")
    return None

# Vercel handler
def handler(environ, start_response):
    """
    Wrap the Flask app as a WSGI application for Vercel.
    """
    return app(environ, start_response)

if __name__ == '__main__':
    app.run(debug=True)
