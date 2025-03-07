from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import qrcode  # Import QR code library
import uuid  # For generating unique IDs

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Database setup
def get_db_connection():
    conn = sqlite3.connect('quick_care.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create users table if it doesn't exist
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

# Initialize the database
init_db()

# Ensure the QR code folder exists
QR_FOLDER = "static/qr_codes"
os.makedirs(QR_FOLDER, exist_ok=True)

# Route to serve the home page
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

# Route to handle user registration
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
                conn.execute('''
                    INSERT INTO users (username, password)
                    VALUES (?, ?)
                ''', (username, hashed_password))
                conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

# Route to handle user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('login'))

        with get_db_connection() as conn:
            user = conn.execute('''
                SELECT * FROM users WHERE username = ?
            ''', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# Route to handle user logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# Route to generate QR Code
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    full_name = request.form.get('full_name')
    mobile = request.form.get('mobile')
    vehicle = request.form.get('vehicle')

@app.route('/emergency-info')
def emergency_info():
    name = request.args.get('name', 'Unknown')
    mobile = request.args.get('mobile', 'Not provided')
    vehicle = request.args.get('vehicle', 'Not provided')
    
    return render_template('emergency_info.html', name=name, mobile=mobile, vehicle=vehicle)    

    if not full_name or not mobile or not vehicle:
        flash("All fields are required!", "error")
        return redirect(url_for('home'))

    # Generate a unique ID for the QR code
    qr_id = str(uuid.uuid4())

    # Store the details in the session with the unique ID
    qr_data = {
        'full_name': full_name,
        'mobile': mobile,
        'vehicle': vehicle
    }
    session[qr_id] = qr_data

    # Generate a URL for the details page
    details_url = url_for('show_details', qr_id=qr_id, _external=True)

    # Generate the QR code with the URL
    qr_img = qrcode.make(details_url)

    # Save the QR code image
    qr_filename = f"{full_name.replace(' ', '_')}_{qr_id}.png"
    qr_path = os.path.join(QR_FOLDER, qr_filename)
    qr_img.save(qr_path)

    return render_template("home.html", qr_image=qr_filename)

# Route to display details when QR code is scanned
@app.route('/details/<qr_id>')
def show_details(qr_id):
    # Retrieve the details from the session
    qr_data = session.get(qr_id)

    if not qr_data:
        flash("Invalid QR code or data not found!", "error")
        return redirect(url_for('home'))

    # Render a template to display the details
    return render_template('details.html', qr_data=qr_data)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0', port=5000 , debug=True)