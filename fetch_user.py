import sqlite3

def get_user_by_vehicle(vehicle):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE vehicle = ?", (vehicle,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return user  # Returns (id, name, mobile, vehicle)
    else:
        return None

# Example Usage
# print(get_user_by_vehicle("KA01AB1234"))