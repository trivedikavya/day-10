import json
from datetime import datetime
import uuid

# --- 1. PRODUCT CATALOG ---
# Ensure images 1.png to 6.png exist in frontend/products/
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
    Smarter search that checks Name, Category, and Color.
    """
    results = CATALOG
    if not filters:
        return results

    filtered = []
    for p in results:
        match = True
        
        # Create a "Searchable String" for the product (Name + Category + Color)
        # We normalize by lowercasing and removing dashes (t-shirt -> tshirt)
        p_text = f"{p['name']} {p['category']} {p['color']}".lower().replace("-", " ")
        
        # 1. CATEGORY CHECK
        if 'category' in filters and filters['category']:
            search_term = filters['category'].lower().replace("-", " ")
            # If the search term is NOT in the product text, fail.
            # This allows "Denim Jacket" to match "Vintage Denim Jacket"
            if search_term not in p_text:
                match = False

        # 2. COLOR CHECK
        if 'color' in filters and filters['color']:
            color_term = filters['color'].lower()
            if color_term not in p_text:
                match = False

        # 3. PRICE CHECK
        if 'max_price' in filters and filters['max_price']:
            try:
                if p['price'] > int(filters['max_price']):
                    match = False
            except:
                pass
        
        if match:
            filtered.append(p)
            
    return filtered

def create_order(items):
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

    try:
        with open(ORDERS_FILE, "a") as f:
            f.write(json.dumps(order) + "\n")
    except Exception as e:
        print(f"Error saving order: {e}")

    return order

def get_last_order():
    try:
        with open(ORDERS_FILE, "r") as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        return None
    return None