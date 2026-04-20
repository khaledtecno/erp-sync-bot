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

erp_api_key = "cf5d4f31c4ef20d"
erp_api_secret = "b3309adb7a0a908"

erp_headers = {
    "Authorization": f"token {erp_api_key}:{erp_api_secret}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ⚠️ إعدادات هامة جداً لأوامر البيع (Sales Orders)
ERP_COMPANY = "Miss Akakos" # 📌 تأكد أن هذا هو اسم الشركة بالضبط كما في إعدادات ERPNext
ERP_DEFAULT_CUSTOMER = "WooCommerce Customer" # 📌 يجب إنشاء عميل بهذا الاسم في ERPNext أولاً

# ==========================================
# 3. دالة سحب المنتجات (الكود الخاص بك)
# ==========================================
def sync_products():
    print("--- 📦 جاري سحب المنتجات من WooCommerce ---")
    response = requests.get(f"{woo_base}/products", params=woo_params)

    if response.status_code == 200:
        products = response.json()
        print(f"تم العثور على {len(products)} منتج. جاري الإرسال لـ ERPNext...")
        
        for product in products:
            item_data = {
                "item_code": product['sku'] if product['sku'] else str(product['id']),
                "item_name": product['name'],
                "item_group": "Products",
                "stock_uom": "Nos",
                "description": product['description'],
                "is_stock_item": 1 if product['manage_stock'] else 0
            }
            
            erp_response = requests.post(f"{erp_base_url}/Item", headers=erp_headers, json=item_data)
            
            if erp_response.status_code == 200:
                print(f"✅ تم إضافة: {product['name']}")
            elif erp_response.status_code == 409:
                 print(f"⚠️ المنتج موجود مسبقاً: {product['name']}")
            else:
                print(f"❌ خطأ في إضافة {product['name']}: {erp_response.text}")
    else:
        print(f"حدث خطأ أثناء الاتصال بووكومرس (منتجات): {response.status_code}")

# ==========================================
# 4. دالة سحب الطلبات (الجديدة)
# ==========================================
def sync_orders():
    print("\n--- 🛒 جاري سحب الطلبات من WooCommerce ---")
    # سحب الطلبات اللي حالتها Processing فقط
    params = woo_params.copy()
    params['status'] = 'processing' 
    
    response = requests.get(f"{woo_base}/orders", params=params)
    
    if response.status_code == 200:
        orders = response.json()
        print(f"تم العثور على {len(orders)} طلب (Processing).\n")
        
        for order in orders:
            # تجهيز المنتجات اللي جوه الطلب
            items_list = []
            for item in order['line_items']:
                items_list.append({
                    "item_code": item['sku'] if item['sku'] else str(item['product_id']),
                    "qty": item['quantity'],
                    "rate": item['price']
                })
            
            # تجهيز أمر البيع (Sales Order)
            sales_order_data = {
                "doctype": "Sales Order",
                "customer": ERP_DEFAULT_CUSTOMER,
                "company": ERP_COMPANY,
                "po_no": str(order['id']), # حفظ رقم طلب ووكومرس
                "transaction_date": order['date_created'].split("T")[0],
                "delivery_date": order['date_created'].split("T")[0], 
                "items": items_list
            }
            
            # إرسال الطلب
            res = requests.post(f"{erp_base_url}/Sales Order", headers=erp_headers, json=sales_order_data)
            
            # 🔍 الطباعة التفصيلية لاكتشاف الأخطاء (Debug)
            if res.status_code == 200:
                print(f"✅ تم إنشاء أمر بيع للطلب رقم: {order['id']}")
            elif res.status_code == 409:
                print(f"⚠️ الطلب رقم {order['id']} موجود مسبقاً.")
            else:
                print(f"❌ تم رفض الطلب {order['id']} من ERPNext! تفاصيل الخطأ:")
                print(res.text) # السطر ده هيقولنا المشكلة فين بالظبط
    else:
        print(f"حدث خطأ أثناء الاتصال بووكومرس (طلبات): {response.status_code}")

# ==========================================
# 5. تشغيل السكريبت
# ==========================================
if __name__ == "__main__":
    sync_products()
    sync_orders()
    print("\n🎉 انتهت دورة المزامنة.")
