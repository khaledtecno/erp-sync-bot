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
# 2. إعدادات ERPNext (محدثة بالبيانات الصحيحة)
# ==========================================
erp_base_url = "https://missakakos.z.frappe.cloud/api/resource" 
erp_headers = {
    "Authorization": "token cf5d4f31c4ef20d:b3309adb7a0a908",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# الإعدادات اللي طلعناها من الصور
ERP_COMPANY = "MissAkakos" 
ERP_DEFAULT_CUSTOMER = "WooCommerce Customer"
ERP_DEFAULT_WAREHOUSE = "Stores - MA"

# ==========================================
# 3. دالة مزامنة المنتجات (لضمان وجود الأصناف)
# ==========================================
def sync_products():
    print("--- 📦 جاري مزامنة المنتجات من WooCommerce ---")
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
                "is_stock_item": 1 
            }
            # محاولة إنشاء المنتج لو مش موجود
            requests.post(f"{erp_base_url}/Item", headers=erp_headers, json=item_data)
        print(f"✅ تمت مراجعة {len(products)} منتج.")

# ==========================================
# 4. دالة مزامنة الطلبات (مع حل مشكلة المخزن)
# ==========================================
def sync_orders():
    print("\n--- 🛒 جاري مزامنة الطلبات من WooCommerce ---")
    params = woo_params.copy()
    params['status'] = 'processing' # بيسحب الطلبات قيد التنفيذ فقط
    
    response = requests.get(f"{woo_base}/orders", params=params)
    
    if response.status_code == 200:
        orders = response.json()
        print(f"تم العثور على {len(orders)} طلب جديد.\n")
        
        for order in orders:
            items_list = []
            for item in order['line_items']:
                # تحديد الكود (SKU أو ID)
                i_code = item['sku'] if item['sku'] else str(item['product_id'])
                items_list.append({
                    "item_code": i_code,
                    "qty": item['quantity'],
                    "rate": item['price'],
                    "warehouse": ERP_DEFAULT_WAREHOUSE # تحديد المخزن لكل صنف
                })
            
            # تجهيز بيانات أمر البيع
            sales_order_data = {
                "doctype": "Sales Order",
                "customer": ERP_DEFAULT_CUSTOMER,
                "company": ERP_COMPANY,
                "set_warehouse": ERP_DEFAULT_WAREHOUSE, # تحديد المخزن للأوردر بالكامل
                "po_no": str(order['id']),
                "transaction_date": order['date_created'].split("T")[0],
                "delivery_date": order['date_created'].split("T")[0], 
                "items": items_list
            }
            
            # إرسال الطلب لـ ERPNext
            res = requests.post(f"{erp_base_url}/Sales Order", headers=erp_headers, json=sales_order_data)
            
            if res.status_code == 200:
                print(f"✅ تم بنجاح: إنشاء أمر بيع للطلب رقم {order['id']}")
            elif res.status_code == 409:
                print(f"⚠️ الطلب رقم {order['id']} موجود مسبقاً في النظام.")
            else:
                # طباعة الخطأ بشكل مختصر وواضح
                error_msg = res.json().get('_server_messages', res.text)
                print(f"❌ تم رفض الطلب {order['id']}: {error_msg[:200]}")
    else:
        print(f"❌ خطأ في الاتصال بووكومرس: {response.status_code}")

# ==========================================
# 5. تشغيل البوت
# ==========================================
if __name__ == "__main__":
    sync_products()
    sync_orders()
    print("\n🎉 انتهت دورة المزامنة بنجاح.")
    

