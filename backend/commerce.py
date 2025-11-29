import json
from datetime import datetime
import uuid

# --- 1. PRODUCT CATALOG ---
# Images match your uploaded filenames: 1.png, 2.png, etc.
CATALOG = [
    {"id": "p1", "name": "Classic White Tee", "price": 800, "currency": "INR", "category": "t-shirt", "color": "white", "sizes": ["S", "M", "L"], "image": "1.png"},
    {"id": "p2", "name": "Midnight Black Hoodie", "price": 1500, "currency": "INR", "category": "hoodie", "color": "black", "sizes": ["M", "L", "XL"], "image": "2.png"},
    {"id": "p3", "name": "Vintage Denim Jacket", "price": 2500, "currency": "INR", "category": "jacket", "color": "blue", "sizes": ["M", "L"], "image": "3.png"},
    {"id": "p4", "name": "Ceramic Coffee Mug", "price": 450, "currency": "INR", "category": "mug", "color": "white", "sizes": ["standard"], "image": "4.png"},
    {"id": "p5", "name": "Matte Black Tumbler", "price": 700, "currency": "INR", "category": "mug", "color": "black", "sizes": ["500ml"], "image": "5.png"},
    {"id": "p6", "name": "Graphic Print Tee", "price": 950, "currency": "INR", "category": "t-shirt", "color": "grey", "sizes": ["S", "M", "L", "XL"], "image": "6.png"},
]

ORDERS_FILE = "orders.json"

# --- 2. MERCHANT FUNCTIONS ---

def list_products(filters=None):
    """
    Simulates an API call to search/filter products.
    """
    results = CATALOG
    if not filters:
        return results

    filtered = []
    for p in results:
        match = True
        # Simple case-insensitive matching
        if 'category' in filters and filters['category'] and filters['category'].lower() not in p['category'].lower():
            match = False
        if 'color' in filters and filters['color'] and filters['color'].lower() not in p['color'].lower():
            match = False
        if 'max_price' in filters and filters['max_price'] and p['price'] > int(filters['max_price']):
            match = False
        
        if match:
            filtered.append(p)
    return filtered

def create_order(items):
    """
    Creates an order object and saves it.
    """
    total = 0
    order_items = []
    
    for item in items:
        # Find product
        product = next((p for p in CATALOG if p['id'] == item['product_id']), None)
        if product:
            cost = product['price'] * item.get('quantity', 1)
            total += cost
            order_items.append({
                "product_name": product['name'],
                "quantity": item.get('quantity', 1),
                "size": item.get('size', 'N/A'),
                "price": product['price'],
                "subtotal": cost,
                "image": product['image']
            })

    order = {
        "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
        "timestamp": datetime.now().isoformat(),
        "items": order_items,
        "total_amount": total,
        "currency": "INR",
        "status": "confirmed"
    }

    # Persist to file
    try:
        with open(ORDERS_FILE, "a") as f:
            f.write(json.dumps(order) + "\n")
    except Exception as e:
        print(f"Error saving order: {e}")

    return order

def get_last_order():
    """Reads the last line of the orders file."""
    try:
        with open(ORDERS_FILE, "r") as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        return None
    return None