import sqlite3
import pandas as pd
import hashlib
from flask import Flask, app, request, render_template, jsonify
def extract_unique_menu(csv_file):
    """Extract unique menu items from the provided CSV file."""
    df = pd.read_csv(csv_file)
    unique_items = df[['Item Name', 'Product Price']].drop_duplicates()
    # Create a list of tuples (Item Name, Product Price)
    menu_items = [(row['Item Name'], row['Product Price']) for _, row in unique_items.iterrows()]
    return menu_items

def setup_database(csv_file):
    """Setup the database and create necessary tables."""
    conn = sqlite3.connect('food_order_chatbot.db')
    c = conn.cursor()

    # Drop existing tables (if they exist)
    c.execute('DROP TABLE IF EXISTS bills')
    c.execute('DROP TABLE IF EXISTS orders')
    c.execute('DROP TABLE IF EXISTS items')
    c.execute('DROP TABLE IF EXISTS users')

    # Create the users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')

    # Create the items table
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        popularity INTEGER DEFAULT 0
    )''')

    # Create the orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES items (item_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')

    # Create the bills table
    c.execute('''CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total_cost REAL NOT NULL,
        bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')

    # Insert unique items from the CSV file into the items table
    menu_items = extract_unique_menu(csv_file)
    c.executemany('INSERT INTO items (name, price) VALUES (?, ?)', menu_items)

    conn.commit()
    conn.close()

def generate_bill(user_id):
    """Generate a bill for the specified user."""
    conn = sqlite3.connect('food_order_chatbot.db')
    c = conn.cursor()

    try:
        # Calculate the total cost for the user's orders
        c.execute(''' 
            SELECT SUM(i.price * o.quantity) as total_cost
            FROM orders o
            JOIN items i ON o.item_id = i.item_id
            WHERE o.user_id = ? 
        ''', (user_id,))
        
        result = c.fetchone()
        total_cost = result[0] if result[0] is not None else 0

        # Insert the total cost into the bills table
        c.execute('INSERT INTO bills (user_id, total_cost) VALUES (?, ?)', (user_id, total_cost))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred during bill generation: {e}")
    finally:
        conn.close()


def check_bills_in_database():
    """Check and display data in the bills table."""
    conn = None
    try:
        conn = sqlite3.connect('food_order_chatbot.db')
        c = conn.cursor()
        c.execute('SELECT * FROM bills')
        bills = c.fetchall()

        if not bills:
            print("No data found in the 'bills' table.")
        else:
            print("Data in the 'bills' table:")
            for bill in bills:
                print(bill)
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    setup_database('restaurant-1-orders.csv')  # Pass the CSV file path here

