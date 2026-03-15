import sqlite3

DATABASE = 'lost_found.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    # Initialize schema immediately if run as script
    init_db()
