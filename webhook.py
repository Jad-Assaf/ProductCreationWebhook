from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Your other store's API key and password
API_KEY = os.getenv('API_KEY')
PASSWORD = os.getenv('PASSWORD')
STORE_URL = os.getenv('STORE_URL')

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Parse the incoming JSON data
    data = request.json
    if 'id' in data:  # Ensure it's a product object
        product = data
        create_or_update_product(product)
    return jsonify({'status': 'success'}), 200

def create_or_update_product(product):
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': PASSWORD
    }
    # Use the entire product payload as-is
    payload = {"product": product}

    # Send the request to the other store
    response = requests.post(STORE_URL, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        print("Product created/updated successfully!")
    else:
        print("Error:", response.text)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
    
