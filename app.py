from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
from datetime import datetime
from recommendation import get_recommendations
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import hashlib
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Function to get database connection
def get_db_connection():
    conn = sqlite3.connect('food_order_chatbot.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to get unique values from a CSV file
def get_unique_values_from_csv(file_path, column_name):
    df = pd.read_csv(file_path)
    unique_values = df[column_name].unique().tolist()
    return unique_values

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# User registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"message": "Username and password are required!"}), 400

        conn = get_db_connection()
        c = conn.cursor()
        
        existing_user = c.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            return jsonify({"message": "Username already exists!"}), 400

        hashed_password = generate_password_hash(password)
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registration successful!"}), 201

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Use .get() to avoid KeyError
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"message": "Username and password are required."}), 400

        conn = get_db_connection()
        c = conn.cursor()
        user = c.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            return redirect(url_for('chatbot'))  # Redirect to the chatbot page
        else:
            return jsonify({"message": "Invalid username or password."}), 401

    return render_template('login.html')

@app.route('/chatbot')
def chatbot():
    # Render your chatbot page template here
    return render_template('chatbot.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')  # Render the forgot password HTML page
    
    elif request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        conn = sqlite3.connect('food_order_chatbot.db')
        c = conn.cursor()
        
        # Check if username exists
        c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if user:
            # Update the password in the database without hashing
            c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
            conn.commit()
            message = "Password has been reset successfully."
        else:
            message = "Username not found."

        conn.close()
        return jsonify({"message": message})


# Endpoint to get food recommendations
@app.route('/recommend', methods=['POST'])
def recommend():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    selected_item = request.json.get('selected_item')
    if not selected_item:
        return jsonify({"message": "Selected item is required"}), 400

    recommendations = get_recommendations(selected_item)
    return jsonify({"recommendations": recommendations})

@app.route('/latest_bill', methods=['GET'])
def latest_bill():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db_connection()
    c = conn.cursor()
    latest_bill = c.execute('SELECT total_cost, order_date FROM bills WHERE user_id = ? ORDER BY order_date DESC LIMIT 1',
                             (session['user_id'],)).fetchone()
    conn.close()
    
    if latest_bill:
        total_cost, order_date = latest_bill
        return jsonify({"total_cost": total_cost, "order_date": order_date}), 200
    else:
        return jsonify({"message": "No bills found."}), 404

@app.route('/order', methods=['POST'])
def order():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    items = request.json.get('items', [])
    quantities = request.json.get('quantities', [])
    
    if not items or not quantities:
        return jsonify({"message": "Items and quantities are required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    total_cost = 0
    
    # Insert orders and calculate total cost
    for item_name, quantity in zip(items, quantities):
        item = c.execute('SELECT item_id, price FROM items WHERE name = ?', (item_name,)).fetchone()
        if item:
            item_id, price = item
            item_cost = price * quantity
            total_cost += item_cost
            
            # Debug statement to check item cost
            print(f"Item: {item_name}, Quantity: {quantity}, Price: {price}, Item Cost: {item_cost}")

            # Insert the order into the orders table
            c.execute('INSERT INTO orders (user_id, item_id, quantity, order_date) VALUES (?, ?, ?, ?)', 
                      (session['user_id'], item_id, quantity, datetime.now()))
        else:
            print(f"Item '{item_name}' not found in database.")  # Debug statement
    
    # Check if total_cost is greater than 0 before inserting into bills
    if total_cost > 0:
        try:
            c.execute('INSERT INTO bills (user_id, total_cost) VALUES (?, ?)', 
                      (session['user_id'], total_cost))
            print(f"Inserted bill for user {session['user_id']}: {total_cost}")  # Debug statement
            conn.commit()  # Commit after inserting into bills
        except Exception as e:
            print(f"Failed to insert bill: {e}")  # Catch and print any errors
            conn.rollback()  # Rollback if there’s an error
            return jsonify({"message": "Error saving the bill"}), 500
    else:
        print("No valid items ordered, bill not created.")  # Debug statement
    
    conn.close()
    
    return jsonify({"message": "Order placed successfully!", "total_cost": total_cost})

# Endpoint to view order history
@app.route('/order_history', methods=['GET'])
def order_history():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db_connection()
    c = conn.cursor()
    orders = c.execute('''SELECT i.name, o.quantity, o.order_date FROM orders o
                          JOIN items i ON o.item_id = i.item_id
                          WHERE user_id = ?
                          ORDER BY o.order_date DESC''', (session['user_id'],)).fetchall()
    
    order_history = [{"item": row['name'], "quantity": row['quantity'], "date": row['order_date']} for row in orders]
    conn.close()
    return jsonify({"order_history": order_history})

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

# Endpoint to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    response = process_user_message(user_message)
    return jsonify({"reply": response})

# Endpoint to retrieve unique values from CSV
@app.route('/unique_values/csv', methods=['GET'])
def unique_values_csv():
    file_path = r'C:\Users\mohan\Downloads\food\restaurant-1-orders.csv'
    column_name = 'column_name'  # Update this
    unique_values = get_unique_values_from_csv(file_path, column_name)
    return jsonify({"unique_values": unique_values})

# Endpoint to retrieve unique values from the database
@app.route('/unique_values/db', methods=['GET'])
def unique_values_db():
    conn = get_db_connection()
    c = conn.cursor()
    unique_items = c.execute('SELECT DISTINCT name FROM items').fetchall()
    conn.close()
    unique_item_names = [item['name'] for item in unique_items]
    return jsonify({"unique_items": unique_item_names})

# Endpoint to retrieve unique values from both CSV and DB
@app.route('/unique_values', methods=['GET'])
def unique_values():
    csv_unique_values = get_unique_values_from_csv(r'C:\Users\mohan\Downloads\food\restaurant-1-orders.csv', 'column_name')
    conn = get_db_connection()
    c = conn.cursor()
    db_unique_values = c.execute('SELECT DISTINCT name FROM items').fetchall()
    conn.close()
    db_unique_names = [item['name'] for item in db_unique_values]

    return jsonify({
        "csv_unique_values": csv_unique_values,
        "db_unique_values": db_unique_names
    })

# Get menu details function
def get_menu_details():
    conn = sqlite3.connect('food_order_chatbot.db')
    c = conn.cursor()
    items = c.execute('SELECT name, price FROM items').fetchall()
    conn.close()
    return "\n".join([f"{item[0]}: ${item[1]}" for item in items])

# User cart dictionary
user_cart = {}

# Calculate bill function
def calculate_bill():
    total_cost = 0
    for item_name, quantity in user_cart.items():
        item = get_db_item(item_name)
        if item:
            price = item['price']
            total_cost += price * quantity
    return total_cost

# Get database item function
def get_db_item(item_name):
    conn = get_db_connection()
    c = conn.cursor()
    item = c.execute('SELECT price FROM items WHERE LOWER(name) = ?', (item_name.lower(),)).fetchone()
    conn.close()
    return item

# Process user message function
def process_user_message(message):
    global user_cart
    message = message.lower()
    conn = get_db_connection()
    c = conn.cursor()

    if "recommend" in message:
        selected_item = message.replace("recommend", "").strip()
        recommendations = get_recommendations(selected_item)
        conn.close()
        return f"Here are some recommendations for you: {', '.join(recommendations)}"

    elif "menu" in message:
        conn.close()
        return get_menu_details()

    elif "bill" in message:
        total_cost = calculate_bill()
        if total_cost > 0:
            return f"Your total bill is: ${total_cost:.2f}"
        else:
            return "You have no items in your order."

    elif "order" in message:
        items = message.replace("order", "").strip().split(',')
        for item in items:
            item_name = item.strip()
            user_cart[item_name] = user_cart.get(item_name, 0) + 1
        total_cost = calculate_bill()
        return f"You have ordered: {', '.join(user_cart.keys())}. Total cost: ${total_cost:.2f}"

    else:
        conn.close()
        return "I'm sorry, I didn't understand that. You can ask for recommendations, menu, bill, or place an order."

if __name__ == '__main__':
    app.run(debug=True)
