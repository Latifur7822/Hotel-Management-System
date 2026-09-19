LAM International Hotel Management System - Render Fix

যে ফাইলগুলো replace করবেন:
1. app.py
2. templates/dashboard.html
3. templates/guest_registry.html
4. templates/customer_dashboard.html
5. templates/staff_login.html
6. templates/salary_management.html (নতুন)

rooms_management.html, index.html এবং admin_panel.html-ও package-এর মধ্যে রাখা আছে।
Procfile এবং requirements.txt-ও রাখা আছে।

Admin login:
Username: md_latif
Password: md123
Portal: Admin Portal

মূল Render fix:
- dashboard.html-এর incomplete HTML/Jinja block সম্পূর্ণ করা হয়েছে।
- active_count[0] / emp_count[0] ঠিক করে সরাসরি variable ব্যবহার করা হয়েছে।
- bookings dictionary অনুযায়ী template ঠিক করা হয়েছে।
- guest_registry dictionary অনুযায়ী template ঠিক করা হয়েছে।
- customer booking history dictionary অনুযায়ী template ঠিক করা হয়েছে।
- customer booking-এ random room number-এর বদলে available database room নেওয়া হয়েছে।
- DATABASE_PATH absolute করা হয়েছে যাতে Render working directory বদলালেও database path consistent থাকে।
- SECRET_KEY environment variable থেকে নেওয়ার ব্যবস্থা করা হয়েছে।

Render start command (Procfile):
web: gunicorn app:app
