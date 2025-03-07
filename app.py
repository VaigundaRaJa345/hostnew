import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2  # PostgreSQL
import qrcode
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

# Ensure correct database URL format for psycopg2
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    result = urlparse(DATABASE_URL)
    return psycopg2.connect(
        dbname=result.path[1:],  
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )

# Initialize database tables
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS emergency_contacts (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    mobile TEXT NOT NULL UNIQUE,
                    vehicle TEXT NOT NULL UNIQUE
                )
            ''')
            conn.commit()

init_db()

# Ensure QR code folder exists
QR_FOLDER = "static/qr_codes"
os.makedirs(QR_FOLDER, exist_ok=True)

@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    flash("Please log in first!", "warning")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        if not username or not password:
            flash("Username and password are required!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
                    conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        if not username or not password:
            flash("Username and password are required!", "danger")
            return redirect(url_for('login'))

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, password FROM users WHERE username = %s', (username,))
                user = cur.fetchone()

        if user and check_password_hash(user[2], password):
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    full_name = request.form.get('full_name').strip()
    mobile = request.form.get('mobile').strip()
    vehicle = request.form.get('vehicle').strip()

    if not full_name or not mobile or not vehicle:
        return jsonify({"error": "All fields are required!"}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("Connected to DB, inserting data...")  # Debugging
                cur.execute('INSERT INTO emergency_contacts (name, mobile, vehicle) VALUES (%s, %s, %s)',
                            (full_name, mobile, vehicle))
                conn.commit()
                print("Data inserted successfully!")  # Debugging

        # Generate the emergency info URL
        details_url = url_for('emergency_info', name=full_name, mobile=mobile, vehicle=vehicle, _external=True)

        # Generate QR Code
        qr_img = qrcode.make(details_url)
        qr_filename = f"{mobile}.png"
        qr_path = os.path.join(QR_FOLDER, qr_filename)
        qr_img.save(qr_path)
        print("QR Code Generated!")  # Debugging

        return jsonify({"qr_url": url_for('static', filename=f'qr_codes/{qr_filename}', _external=True)})

    except psycopg2.IntegrityError:
        print("Duplicate data error!")  # Debugging
        return jsonify({"error": "Mobile number or Vehicle number already exists!"}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")  # Debugging
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/emergency-info/<int:contact_id>')
def emergency_info(contact_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT name, mobile, vehicle FROM emergency_contacts WHERE id = %s', (contact_id,))
            contact = cur.fetchone()

    if contact:
        return render_template('emergency_info.html', name=contact[0], mobile=contact[1], vehicle=contact[2])
    else:
        return "Contact not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)