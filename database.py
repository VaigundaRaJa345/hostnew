import sqlite3

# Connect to the database (or create it if it doesn't exist)
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create table to store user details
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT UNIQUE NOT NULL,  -- Unique constraint for mobile number
    vehicle TEXT UNIQUE NOT NULL  -- Unique constraint for vehicle number
)
''')

# Save and close the connection
conn.commit()
conn.close()