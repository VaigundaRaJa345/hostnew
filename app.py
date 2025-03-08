import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2  # PostgreSQL
import qrcode
from urllib.parse import urlparse
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your_secret_key")
csrf = CSRFProtect(app)

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
    try:
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
    except Exception as e:
        print("Database initialization failed:", e)

init_db()

# Ensure QR code folder exists
QR_FOLDER = "static/qr_codes"
os.makedirs(QR_FOLDER, exist_ok=True)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

@app.route("/")
def home():
    return render_template("home.html")  # Your form page

@app.route("/generate_qr", methods=["POST"])
def generate_qr():
    full_name = request.form.get("full_name")
    mobile = request.form.get("mobile")
    vehicle = request.form.get("vehicle")

    if not full_name or not mobile or not vehicle:
        return "Missing data", 400

    # Create QR data
    qr_data = f"Name: {full_name}\nMobile: {mobile}\nVehicle: {vehicle}"

    # Generate QR code
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template("qr_display.html", qr_code=qr_base64)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data.strip()

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

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data.strip()

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

        flash("Invalid username or password!", "danger")
        return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/emergency-info/<int:contact_id>')
def emergency_info(contact_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT name, mobile, vehicle FROM emergency_contacts WHERE id = %s', (contact_id,))
                contact = cur.fetchone()

        if not contact:
            flash("Emergency contact not found!", "danger")
            return redirect(url_for('home'))

        return render_template('emergency_info.html', name=contact[0], mobile=contact[1], vehicle=contact[2])
    except Exception as e:
        print("Error fetching emergency contact:", e)
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)