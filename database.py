
import sqlite3

DB_NAME = "inventory.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            price REAL NOT NULL,
            reorder_level INTEGER NOT NULL DEFAULT 5
        )
    """)

    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]

    if "reorder_level" not in columns:
        cursor.execute("""
            ALTER TABLE products
            ADD COLUMN reorder_level INTEGER NOT NULL DEFAULT 5
        """)

   
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            movement_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready!")


if __name__ == "__main__":
    create_database()
