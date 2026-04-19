
import requests
import json

# ==========================================
# 1. إعدادات WooCommerce 
# ==========================================
woo_url = "https://missakakos.com/wp-json/wc/v3/products"
woo_params = {
    "consumer_key": "ck_51c2f9d0104b37710268c51c753c1adc2496454c",
    "consumer_secret": "cs_4c21f9df5fab3ca3482483668627818eae277b16"
}

# ==========================================
# 2. إعدادات ERPNext (تم تحديث الرابط)
# ==========================================
erp_url = "https://missakakos.z.frappe.cloud/api/resource/Item" 

erp_api_key = "cf5d4f31c4ef20d"
erp_api_secret = "b3309adb7a0a908"

erp_headers = {
    "Authorization": f"token {erp_api_key}:{erp_api_secret}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ==========================================
# 3. سحب المنتجات من ووكومرس
# ==========================================
print("جاري سحب المنتجات من WooCommerce...")
response = requests.get(woo_url, params=woo_params)

if response.status_code == 200:
    products = response.json()
    print(f"تم العثور على {len(products)} منتج. جاري الإرسال لـ ERPNext...\n")
    
    # ==========================================
    # 4. إرسال كل منتج إلى ERPNext
    # ==========================================
    for product in products:
        item_data = {
            "item_code": product['sku'] if product['sku'] else str(product['id']),
            "item_name": product['name'],
            "item_group": "Products", # تأكد إن المجموعة دي موجودة في ERPNext
            "stock_uom": "Nos",       # تأكد إن الوحدة دي موجودة (أو غيرها لـ Piece/قطعة)
            "description": product['description'],
            "is_stock_item": 1 if product['manage_stock'] else 0
        }
        
        erp_response = requests.post(erp_url, headers=erp_headers, json=item_data)
        
        if erp_response.status_code == 200:
            print(f"✅ تم إضافة: {product['name']}")
        elif erp_response.status_code == 409:
             print(f"⚠️ المنتج موجود مسبقاً: {product['name']}")
        else:
            print(f"❌ خطأ في إضافة {product['name']}:")
            print(erp_response.text)
            
else:
    print(f"حدث خطأ أثناء الاتصال بووكومرس: {response.status_code}")
