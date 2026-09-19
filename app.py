import os
import random
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lam_international_mega_secure_key')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'hotel.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    # ⚙️ ডাটা সরাসরি ডিকশনারি অবজেক্ট হিসেবে পড়ার জন্য মেইন কানেকশনে রো-ফ্যাক্টরি সেট করা হলো
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ইউজার টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            status TEXT DEFAULT 'Active'
        )
    ''')
    
    # বুকিং টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT,
            room_type TEXT,
            room_number TEXT,
            nights INTEGER,
            payment_status TEXT DEFAULT 'Unpaid',
            status TEXT DEFAULT 'Confirmed'
        )
    ''')
    
    # রুম টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotel_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE,
            room_type TEXT,
            price_per_night INTEGER,
            status TEXT DEFAULT 'Available'
        )
    ''')

    # 💰 স্যালারি ম্যানেজমেন্ট টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            username TEXT,
            basic_salary INTEGER DEFAULT 0,
            bonus INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'Unpaid',
            payout_date TEXT DEFAULT 'Pending'
        )
    ''')
    
    # ডেমো রুম তৈরি (রো-ফ্যাক্টরি সামঞ্জস্যপূর্ণ কাউন্টার লজিক ফিক্সড)
    cursor.execute("SELECT COUNT(*) AS total FROM hotel_rooms")
    if cursor.fetchone()['total'] == 0:
        demo_rooms = [
            ('101', 'Deluxe Suite', 150, 'Available'),
            ('102', 'Deluxe Suite', 150, 'Occupied'),
            ('201', 'Executive Room', 100, 'Available'),
            ('202', 'Executive Room', 100, 'Available'),
            ('301', 'Standard Room', 60, 'Available')
        ]
        cursor.executemany("INSERT INTO hotel_rooms (room_number, room_type, price_per_night, status) VALUES (?, ?, ?, ?)", demo_rooms)
    
    # ডিফল্ট MD অ্যাকাউন্ট
    cursor.execute("SELECT * FROM users WHERE username='md_latif'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)", 
                       ('md_latif', 'md123', 'MD', 'Active'))
        
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

# 💼 সিকিউর স্টাফ লগইন
@app.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form['role_type']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, status FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            user_id = user['id']
            user_role = user['role']
            user_status = user['status']
            
            if user_status == 'Terminated':
                error = "দুঃখিত! এই অ্যাকাউন্টটি বরখাস্ত করা হয়েছে।"
                return render_template('staff_login.html', error=error)
            
            if selected_role == 'admin' and user_role in ['MD', 'admin']:
                session['staff_id'] = user_id
                session['staff_user'] = username
                session['staff_role'] = user_role
                return redirect(url_for('dashboard'))
            elif selected_role == 'employee' and user_role == 'employee':
                session['staff_id'] = user_id
                session['staff_user'] = username
                session['staff_role'] = user_role
                return redirect(url_for('dashboard'))
            else:
                error = "অনুমতি নেই! সঠিক পোর্টাল সিলেক্ট করুন।"
        else:
            error = "ভুল ইউজারনেম অথবা পাসওয়ার্ড দিয়েছেন!"
            
    return render_template('staff_login.html', error=error)

# 📊 মূল সেন্ট্রাল ড্যাশবোর্ড
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'staff_user' not in session:
        return redirect(url_for('staff_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST' and 'action_type' in request.form:
        new_user = request.form['username']
        new_pass = request.form['password']
        new_role = request.form['role']
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (new_user, new_pass, new_role))
            conn.commit()
            
            cursor.execute("SELECT id FROM users WHERE username=?", (new_user,))
            s_id = cursor.fetchone()['id']
            cursor.execute("INSERT INTO payroll (staff_id, username) VALUES (?, ?)", (s_id, new_user))
            conn.commit()
        except Exception: pass

    if request.method == 'POST' and 'terminate_id' in request.form:
        cursor.execute("UPDATE users SET status='Terminated' WHERE id=?", (request.form['terminate_id'],))
        conn.commit()

    if request.method == 'POST' and 'cancel_booking_id' in request.form:
        cursor.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (request.form['cancel_booking_id'],))
        conn.commit()

    cursor.execute("SELECT username, role, status, id FROM users WHERE role != 'MD' AND role != 'customer'")
    raw_staffs = cursor.fetchall()
    staffs = [{'username': s['username'], 'role': s['role'], 'status': s['status'], 'id': s['id']} for s in raw_staffs]
    
    cursor.execute("SELECT id, guest_name, room_type, room_number, nights, payment_status, status FROM bookings")
    raw_bookings = cursor.fetchall()
    bookings = [{'id': b['id'], 'guest_name': b['guest_name'], 'room_type': b['room_type'], 'room_number': b['room_number'], 'nights': b['nights'], 'payment_status': b['payment_status'], 'status': b['status']} for b in raw_bookings]
    
    # ⚙️ কাউন্টার অবজেক্টগুলোর ইন্ডেক্সিং এরর ফিক্স করা হয়েছে
    cursor.execute("SELECT COUNT(*) AS total FROM bookings WHERE status='Confirmed'")
    active_count = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE status='Active' AND role='employee'")
    emp_count = cursor.fetchone()['total']

    cursor.execute("SELECT SUM(basic_salary + bonus) AS total FROM payroll WHERE payment_status='Paid'")
    total_payroll_cost = cursor.fetchone()['total']
    if total_payroll_cost is None: total_payroll_cost = 0

    cursor.close()
    conn.close()
    return render_template('dashboard.html', staffs=staffs, bookings=bookings, active_count=active_count, emp_count=emp_count, total_payroll=total_payroll_cost)

# 🛌 Rooms Management রাউট
@app.route('/rooms', methods=['GET', 'POST'])
def rooms_management():
    if 'staff_user' not in session:
        return redirect(url_for('staff_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST' and 'add_room' in request.form:
        r_num = request.form['room_number']
        r_type = request.form['room_type']
        r_price = request.form['price']
        try:
            cursor.execute("INSERT INTO hotel_rooms (room_number, room_type, price_per_night) VALUES (?, ?, ?)", (r_num, r_type, int(r_price)))
            conn.commit()
        except Exception: pass

    if request.method == 'POST' and 'toggle_status_id' in request.form:
        r_id = request.form['toggle_status_id']
        current_status = request.form['current_status']
        new_status = 'Occupied' if current_status == 'Available' else 'Available'
        cursor.execute("UPDATE hotel_rooms SET status=? WHERE id=?", (new_status, int(r_id)))
        conn.commit()

    cursor.execute("SELECT id, room_number, room_type, price_per_night, status FROM hotel_rooms ORDER BY room_number ASC")
    raw_rooms = cursor.fetchall()
    rooms = [{'id': r['id'], 'room_number': r['room_number'], 'room_type': r['room_type'], 'price_per_night': r['price_per_night'], 'status': r['status']} for r in raw_rooms]
    
    cursor.close()
    conn.close()
    return render_template('rooms_management.html', rooms=rooms)

# 👥 Guest Registry রাউট
@app.route('/guests')
def guest_registry():
    if 'staff_user' not in session:
        return redirect(url_for('staff_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT guest_name, room_type, room_number FROM bookings WHERE status='Confirmed'")
    raw_guests = cursor.fetchall()
    guests = [{'guest_name': g['guest_name'], 'room_type': g['room_type'], 'room_number': g['room_number']} for g in raw_guests]
    cursor.close()
    conn.close()
    return render_template('guest_registry.html', guests=guests)

# 💰 স্যালারি ম্যানেজমেন্ট রাউট
@app.route('/salary', methods=['GET', 'POST'])
def salary_management():
    if 'staff_user' not in session:
        return redirect(url_for('staff_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST' and 'update_payroll_id' in request.form:
        if session['staff_role'] == 'employee':
            return "Your are not authorized!", 403
            
        p_id = request.form['update_payroll_id']
        salary = request.form['basic_salary']
        p_id = request.form['update_payroll_id']
        salary = request.form['basic_salary']
        bonus = request.form['bonus']
        today = datetime.today().strftime('%Y-%m-%d')
        
        cursor.execute("UPDATE payroll SET basic_salary=?, bonus=?, payment_status='Paid', payout_date=? WHERE id=?", 
                       (int(salary), int(bonus), today, int(p_id)))
        conn.commit()
        return redirect(url_for('salary_management'))
        
    if session['staff_role'] in ['MD', 'admin']:
        cursor.execute("SELECT id, username, basic_salary, bonus, payment_status, payout_date FROM payroll")
    else:
        cursor.execute("SELECT id, username, basic_salary, bonus, payment_status, payout_date FROM payroll WHERE username=?", (session['staff_user'],))
        
    raw_payroll = cursor.fetchall()
    payroll_data = [{'id': p['id'], 'username': p['username'], 'basic_salary': p['basic_salary'], 'bonus': p['bonus'], 'payment_status': p['payment_status'], 'payout_date': p['payout_date']} for p in raw_payroll]
        
    cursor.close()
    conn.close()
    return render_template('salary_management.html', payrolls=payroll_data)

# 👥 কাস্টমার পোর্টাল অথরাইজেশন লজিক
@app.route('/customer-auth', methods=['POST'])
def customer_auth():
    action = request.form.get('action')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == 'signup':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'customer')", (email, password))
            conn.commit()
            cursor.execute("SELECT last_insert_rowid()")
            customer_id = cursor.fetchone()
            # ⚙️ টাপল অবজেক্ট থেকে পিউর আইডি আলাদা করা হলো
            session['customer_id'] = customer_id[0]
            session['customer_name'] = fullname
            cursor.close()
            conn.close()
            return redirect(url_for('customer_dashboard'))
        except Exception:
            cursor.close()
            conn.close()
            return "Email already registered!"
            
    elif action == 'signin':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT id, username FROM users WHERE username=? AND password=? AND role='customer'", (email, password))
        customer = cursor.fetchone()
        
        if customer:
            session['customer_id'] = customer['id']
            # ⚙️ স্ট্রিং ড্রাইভার ক্র্যাশ এরর এখানে শতভাগ ফিক্সড
            display_name = customer['username'].split('@')[0].capitalize()
            session['customer_name'] = display_name
            cursor.close()
            conn.close()
            return redirect(url_for('customer_dashboard'))
        else:
            cursor.close()
            conn.close()
            return "Wrong credentials!"

# 🏨 কাস্টমার ড্যাশবোর্ড প্যানেল
@app.route('/customer-dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('home'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        room_type = request.form['room_type']
        nights = int(request.form['nights'])

        room_map = {
            'Deluxe Suite ($150)': 'Deluxe Suite',
            'Executive Room ($100)': 'Executive Room',
            'Standard Room ($60)': 'Standard Room',
            'Deluxe Suite': 'Deluxe Suite',
            'Executive Room': 'Executive Room',
            'Standard Room': 'Standard Room'
        }
        selected_type = room_map.get(room_type, room_type)

        cursor.execute(
            "SELECT room_number FROM hotel_rooms WHERE room_type=? AND status='Available' ORDER BY room_number LIMIT 1",
            (selected_type,)
        )
        available_room = cursor.fetchone()

        if not available_room:
            cursor.close()
            conn.close()
            return "Sorry, no available room of this type is currently available.", 409

        room_number = available_room['room_number']
        cursor.execute(
            "INSERT INTO bookings (guest_name, room_type, room_number, nights) VALUES (?, ?, ?, ?)",
            (str(session['customer_name']), selected_type, room_number, nights)
        )
        cursor.execute(
            "UPDATE hotel_rooms SET status='Occupied' WHERE room_number=?",
            (room_number,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('customer_dashboard'))
        
    cursor.execute("SELECT room_type, room_number, nights, payment_status, status FROM bookings WHERE guest_name=?", (session['customer_name'],))
    raw_my_bookings = cursor.fetchall()
    my_bookings = [{'room_type': m['room_type'], 'room_number': m['room_number'], 'nights': m['nights'], 'payment_status': m['payment_status'], 'status': m['status']} for m in raw_my_bookings]
    
    cursor.close()
    conn.close()
    return render_template('customer_dashboard.html', bookings=my_bookings)

# 🚪 সেশন লগআউট রাউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# 🚀 মেইন গেটওয়ে রানটাইম (সিন্ট্যাক্স ফিক্সড)
if __name__ == '__main__':
    app.run(debug=True)
