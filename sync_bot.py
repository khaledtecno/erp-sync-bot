import requests
import json

# ==========================================
# 1. إعدادات WooCommerce 
# ==========================================
woo_base = "https://missakakos.com/wp-json/wc/v3"
woo_params = {
    "consumer_key": "ck_51c2f9d0104b37710268c51c753c1adc2496454c",
    "consumer_secret": "cs_4c21f9df5fab3ca3482483668627818eae277b16"
}

# ==========================================
# 2. إعدادات ERPNext 
# ==========================================
erp_base_url = "https://missakakos.z.frappe.cloud/api/resource" 
erp_headers = {
    "Authorization": "token cf5d4f31c4ef20d:b3309adb7a0a908",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

ERP_COMPANY = "MissAkakos" 
ERP_DEFAULT_WAREHOUSE = "Stores - MA"

# ==========================================
# 3. دالة جلب أو إنشاء العميل (Customer)
# ==========================================
def get_or_create_customer(order_billing):
    email = order_billing.get('email')
    full_name = f"{order_billing.get('first_name')} {order_billing.get('last_name')}".strip()
    phone = order_billing.get('phone')

    # البحث عن العميل بالإيميل
    search_url = f"{erp_base_url}/Customer?filters=[[\"email_id\", \"=\", \"{email}\"]]"
    res = requests.get(search_url, headers=erp_headers)
    
    if res.status_code == 200 and res.json().get('data'):
        customer_id = res.json()['data'][0]['name']
        print(f"✅ تم العثور على العميل: {customer_id}")
        return customer_id
    else:
        # إنشاء عميل جديد إذا لم يوجد
        customer_data = {
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": phone
        }
        create_res = requests.post(f"{erp_base_url}/Customer", headers=erp_headers, json=customer_data)
        if create_res.status_code == 200:
            new_id = create_res.json()['data']['name']
            print(f"✨ تم إنشاء سجل عميل جديد: {new_id}")
            return new_id
    return "Guest" # كحالة احتياطية

# ==========================================
# 4. دالة مزامنة وتحديث المنتجات
# ==========================================
def sync_products():
    print("--- 📦 جاري مزامنة وتحديث المنتجات ---")
    response = requests.get(f"{woo_base}/products", params=woo_params)
    if response.status_code == 200:
        products = response.json()
        for product in products:
            item_code = product['sku'] if product['sku'] else str(product['id'])
            item_data = {
                "item_code": item_code,
                "item_name": product['name'],
                "item_group": "Products",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "standard_rate": float(product.get('price', 0)) # تحديث السعر
            }
            
            # محاولة التحديث أولاً
            update_res = requests.put(f"{erp_base_url}/Item/{item_code}", headers=erp_headers, json=item_data)
            
            if update_res.status_code == 200:
                print(f"🔄 تم تحديث بيانات وسعر المنتج: {item_code}")
            elif update_res.status_code == 404:
                # إذا لم يوجد، نقوم بإنشائه
                requests.post(f"{erp_base_url}/Item", headers=erp_headers, json=item_data)
                print(f"✨ تم إضافة منتج جديد: {item_code}")

# ==========================================
# 5. دالة مزامنة الطلبات ببيانات عملاء حقيقية
# ==========================================
def sync_orders():
    print("\n--- 🛒 جاري مزامنة الطلبات التفصيلية ---")
    params = woo_params.copy()
    params['status'] = 'processing'
    
    response = requests.get(f"{woo_base}/orders", params=params)
    
    if response.status_code == 200:
        orders = response.json()
        for order in orders:
            # الحصول على معرف العميل الحقيقي
            erp_customer = get_or_create_customer(order['billing'])
            
            items_list = []
            for item in order['line_items']:
                i_code = item['sku'] if item['sku'] else str(item['product_id'])
                items_list.append({
                    "item_code": i_code,
                    "qty": item['quantity'],
                    "rate": item['price'],
                    "warehouse": ERP_DEFAULT_WAREHOUSE
                })
            
            sales_order_data = {
                "doctype": "Sales Order",
                "customer": erp_customer,
                "company": ERP_COMPANY,
                "set_warehouse": ERP_DEFAULT_WAREHOUSE,
                "po_no": str(order['id']),
                "transaction_date": order['date_created'].split("T")[0],
                "delivery_date": order['date_created'].split("T")[0], 
                "items": items_list,
                "billing_address": f"{order['billing']['address_1']}, {order['billing']['city']}"
            }
            
            res = requests.post(f"{erp_base_url}/Sales Order", headers=erp_headers, json=sales_order_data)
            
            if res.status_code == 200:
                print(f"✅ نجاح: أمر بيع للعميل {order['billing']['first_name']} - طلب رقم {order['id']}")
            elif res.status_code == 409:
                print(f"⚠️ الطلب {order['id']} موجود مسبقاً.")

if __name__ == "__main__":
    sync_products()
    sync_orders()
    print("\n🎉 تمت عملية المزامنة الشاملة بنجاح.")
    
