from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2  # PostgreSQL
import os
import qrcode
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database URL from Render (Replace this with your actual database URL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://quick_care_user:0SM3EPvLjGsVr8LCFNPcotpNahYME0pH@dpg-cv5bp5q3esus73aridg0-a/quick_care")

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
    return redirect(url_for('login'))

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Username and password are required!", "error")
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
            flash("Username already exists!", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('login'))

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cur.fetchone()

        if user and check_password_hash(user[2], password):  # user[2] is password hash
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# User Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# Generate QR Code and Store Data
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    full_name = request.form.get('full_name')
    mobile = request.form.get('mobile')
    vehicle = request.form.get('vehicle')

    if not full_name or not mobile or not vehicle:
        flash("All fields are required!", "error")
        return redirect(url_for('home'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO emergency_contacts (name, mobile, vehicle) VALUES (%s, %s, %s)', 
                            (full_name, mobile, vehicle))
                conn.commit()
    except psycopg2.IntegrityError:
        flash("Mobile number or Vehicle number already exists!", "error")
        return redirect(url_for('home'))

    # Generate a URL containing user details
    details_url = url_for('emergency_info', name=full_name, mobile=mobile, vehicle=vehicle, _external=True)

    # Generate QR code with embedded data
    qr_img = qrcode.make(details_url)

    qr_filename = f"{full_name.replace(' ', '_')}.png"
    qr_path = os.path.join(QR_FOLDER, qr_filename)
    qr_img.save(qr_path)

    return render_template("home.html", qr_image=qr_filename, qr_url=details_url)

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