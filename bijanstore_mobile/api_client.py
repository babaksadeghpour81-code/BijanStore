import requests
from state import AppState

# ⚠️ اگر روی گوشی واقعی تست می‌کنی، آدرس زیر رو به IP کامپیوترت تغییر بده
API_BASE = "http://127.0.0.1:8000/api/v1"

def _headers():
    headers = {"Content-Type": "application/json"}
    if AppState.access_token:
        headers["Authorization"] = f"Bearer {AppState.access_token}"
    return headers


def get_products(search=""):
    url = f"{API_BASE}/products/"
    params = {}
    if search:
        params["search"] = search
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []


def login(username, password):
    url = f"{API_BASE}/auth/token/"
    response = requests.post(url, json={"username": username, "password": password})
    if response.status_code == 200:
        data = response.json()
        AppState.set_tokens(data["access"], data["refresh"], username)
        return True, "ورود موفق"
    return False, "نام کاربری یا رمز عبور اشتباه است"


def get_cart():
    url = f"{API_BASE}/cart/"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return None


def add_to_cart(product_id, quantity=1):
    url = f"{API_BASE}/cart/add/"
    response = requests.post(
        url,
        json={"product_id": product_id, "quantity": quantity},
        headers=_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


def update_cart_item(item_id, quantity):
    url = f"{API_BASE}/cart/update/"
    response = requests.post(
        url,
        json={"item_id": item_id, "quantity": quantity},
        headers=_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


def remove_from_cart(item_id):
    url = f"{API_BASE}/cart/remove/"
    response = requests.post(
        url,
        json={"item_id": item_id},
        headers=_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


def checkout(data):
    url = f"{API_BASE}/orders/checkout/"
    response = requests.post(url, json=data, headers=_headers())
    if response.status_code == 201:
        return True, response.json()
    return False, response.json()


def get_orders():
    url = f"{API_BASE}/orders/"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return []


def get_order_detail(order_number):
    url = f"{API_BASE}/orders/{order_number}/"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return None


def get_notifications():
    url = f"{API_BASE}/notifications/"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return []


def mark_notification_read(notification_id):
    url = f"{API_BASE}/notifications/{notification_id}/read/"
    response = requests.post(url, headers=_headers())
    return response.status_code == 200

def get_order_status(order_number):
    url = f"{API_BASE}/orders/{order_number}/status/"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return None


def start_payment(order_number):
    """درخواست لینک پرداخت"""
    url = f"{API_BASE}/orders/{order_number}/pay/"
    response = requests.post(url, headers=_headers())
    if response.status_code == 200:
        return response.json()
    return None

def delete_order(order_number):
    url = f"{API_BASE}/orders/{order_number}/delete/"
    response = requests.post(url, headers=_headers())
    return response.status_code == 200

