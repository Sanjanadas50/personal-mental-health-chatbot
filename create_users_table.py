import sqlite3

conn = sqlite3.connect('database.db')  # make sure this is your actual DB file
c = conn.cursor()

# Create users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT
)
''')

conn.commit()
conn.close()
print("✅ users table created successfully!")