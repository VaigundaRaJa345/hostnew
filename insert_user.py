import sqlite3

def insert_user(name, mobile, vehicle):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO users (name, mobile, vehicle) VALUES (?, ?, ?)", (name, mobile, vehicle))
        conn.commit()
        print("User added successfully!")
    except sqlite3.IntegrityError:
        print("Error: Mobile number or vehicle number already exists!")
    
    conn.close()