from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2  # PostgreSQL
import os
import qrcode
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# Database URL from Render (Ensure it's set in environment variables)
DATABASE_URL = os.getenv("dpg-cv5bp5q3esus73aridg0-a.oregon-postgres.render.com")

# Connect to PostgreSQL
def get_db_connection():
    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn

# Create tables if they don't exist
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

# Initialize the database
init_db()

# Ensure QR code folder exists
QR_FOLDER = "static/qr_codes"
os.makedirs(QR_FOLDER, exist_ok=True)

# Home route
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    flash("Please log in first!", "warning")
    return redirect(url_for('login'))

# User Registration
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

# User Login
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
                cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cur.fetchone()

        if user and check_password_hash(user[2], password):
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# User Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Generate QR Code and Store Data
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
                cur.execute('INSERT INTO emergency_contacts (name, mobile, vehicle) VALUES (%s, %s, %s)',
                            (full_name, mobile, vehicle))
                conn.commit()
    except psycopg2.IntegrityError:
        return jsonify({"error": "Mobile number or Vehicle number already exists!"}), 400

    # Generate a URL containing user details
    details_url = url_for('emergency_info', name=full_name, mobile=mobile, vehicle=vehicle, _external=True)

    # Generate QR code with embedded data
    qr_img = qrcode.make(details_url)
    qr_filename = f"{mobile}.png"  # Ensure uniqueness using mobile number
    qr_path = os.path.join(QR_FOLDER, qr_filename)
    qr_img.save(qr_path)

    return jsonify({"qr_url": url_for('static', filename=f'qr_codes/{qr_filename}', _external=True)})

# Display Emergency Details When QR is Scanned
@app.route('/emergency-info')
def emergency_info():
    name = request.args.get('name', 'Unknown')
    mobile = request.args.get('mobile', 'Not provided')
    vehicle = request.args.get('vehicle', 'Not provided')

    return render_template('emergency_info.html', name=name, mobile=mobile, vehicle=vehicle)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)