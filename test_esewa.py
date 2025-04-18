import requests
import hmac
import hashlib
import base64

def generate_signature(total_amount, transaction_uuid, product_code, secret_key):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    return base64.b64encode(hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()).decode('utf-8')

url = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
data = {
    "amount": 1000,
    "tax_amount": 0,
    "total_amount": 1000,
    "transaction_uuid": "test-uuid-123",
    "product_code": "EPAYTEST",
    "success_url": "http://localhost:5000/payment_success",
    "failure_url": "http://localhost:5000/payment_failure",
    "signature": generate_signature(1000, "test-uuid-123", "EPAYTEST", "8gBm/:&EnhH.1/q")
}

try:
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {str(e)}")