from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %b %Y, %I:%M %p'):
    if value:
        return datetime.fromisoformat(value).strftime(format)
    return ""

@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    sql = "SELECT * FROM items WHERE 1=1"
    params = []

    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend((f'%{query}%', f'%{query}%'))

    if min_price is not None:
        sql += " AND price >= ?"
        params.append(min_price)

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

    conn = get_db_connection()
    items = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template('index.html', items=items)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            conn.close()
            return "Email already registered!", 400

        conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('index'))
        else:
            return "Invalid credentials!", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items WHERE user_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('profile.html', items=items)

@app.route('/post_item', methods=['GET', 'POST'])
def post_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        user_id = session['user_id']
        photo = request.files['photo']
        photo_filename = None

        if photo and photo.filename:
            photo_filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        auction_end_time = (datetime.now() + timedelta(minutes=2)).isoformat()

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO items (title, description, price, user_id, photo_filename, highest_bid, auction_end_time, is_closed)
            VALUES (?, ?, ?, ?, ?, NULL, ?, 0)
        ''', (title, description, price, user_id, photo_filename, auction_end_time))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('post_item.html')

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()

    if item and item['user_id'] == session['user_id']:
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.execute('DELETE FROM bids WHERE item_id = ?', (item_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('profile'))
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3

@app.route('/view_item/<int:item_id>', methods=['GET', 'POST'])
def view_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch item details
    item = cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return redirect(url_for('index'))

    item = dict(item)

    # Auction closing check & update DB
    auction_end_time = item.get('auction_end_time')
    if auction_end_time and datetime.now() > datetime.fromisoformat(auction_end_time):
        item['is_closed'] = True
        cursor.execute("UPDATE items SET is_closed = 1 WHERE id = ?", (item_id,))
        conn.commit()
    else:
        item['is_closed'] = False

    # Handle bid submission
    if request.method == 'POST' and 'bid_amount' in request.form:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        bid_amount = float(request.form['bid_amount'])
        current_highest = cursor.execute(
            "SELECT MAX(amount) FROM bids WHERE item_id = ?", (item_id,)
        ).fetchone()[0] or item['price']

        if bid_amount > current_highest:
            bid_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "INSERT INTO bids (item_id, bidder_id, amount, bid_time) VALUES (?, ?, ?, ?)",
                (item_id, session['user_id'], bid_amount, bid_time)
            )
            conn.commit()
            return redirect(url_for('view_item', item_id=item_id))

    # Fetch the highest bid and its user
    highest_bid = cursor.execute(
        "SELECT * FROM bids WHERE item_id = ? ORDER BY amount DESC LIMIT 1", (item_id,)
    ).fetchone()

    highest_bid_username = None
    highest_bid_user_id = None
    if highest_bid:
        highest_bid_user_id = highest_bid['bidder_id']
        highest_bid_username_row = cursor.execute(
            "SELECT name FROM users WHERE id = ?", (highest_bid_user_id,)
        ).fetchone()
        if highest_bid_username_row:
            highest_bid_username = highest_bid_username_row['name']
        item['highest_bid'] = highest_bid['amount']
        item['highest_bid_user_id'] = highest_bid_user_id
    else:
        item['highest_bid'] = None

    # Check payment status
    payment_done = False
    if item['is_closed'] and 'user_id' in session:
        payment_done = cursor.execute(
            "SELECT * FROM payments WHERE item_id = ? AND buyer_id = ?",
            (item_id, session.get('user_id'))
        ).fetchone()

    # Fetch bid history
    bids = cursor.execute("""
        SELECT b.amount, u.name AS bidder_name, b.bid_time AS bid_time 
        FROM bids b JOIN users u ON b.bidder_id = u.id 
        WHERE b.item_id = ? ORDER BY b.bid_time DESC
    """, (item_id,)).fetchall()

    conn.close()

    return render_template(
        'view_item.html',
        item=item,
        highest_bid=highest_bid,
        highest_bid_username=highest_bid_username,
        highest_bid_user_id=highest_bid_user_id,
        payment_done=payment_done,
        bids=bids,
        auction_closed=item['is_closed']
    )
@app.route('/debug_items')
def debug_items():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return str([dict(i) for i in items])


@app.route('/chat/<int:item_id>/<int:receiver_id>', methods=['GET', 'POST'])
def chat(item_id, receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    receiver = conn.execute('SELECT * FROM users WHERE id = ?', (receiver_id,)).fetchone()

    if not item or not receiver:
        conn.close()
        return "Item or User not found", 404

    if request.method == 'POST':
        message = request.form['message']
        conn.execute('''
            INSERT INTO chats (sender_id, receiver_id, item_id, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], receiver_id, item_id, message, datetime.now().isoformat()))
        conn.commit()

    messages = conn.execute('''
        SELECT c.*, u.name as sender_name
        FROM chats c
        JOIN users u ON c.sender_id = u.id
        WHERE c.item_id = ? AND ((c.sender_id = ? AND c.receiver_id = ?) OR (c.sender_id = ? AND c.receiver_id = ?))
        ORDER BY c.timestamp ASC
    ''', (item_id, session['user_id'], receiver_id, receiver_id, session['user_id'])).fetchall()

    conn.close()
    return render_template('chat_with_seller.html', item=item, receiver=receiver, chats=messages)

@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    messages = conn.execute('''
        SELECT m.item_id, i.title, u.name AS sender_name, MAX(m.timestamp) as last_time
        FROM chats m
        JOIN items i ON m.item_id = i.id
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        GROUP BY m.item_id, m.sender_id
        ORDER BY last_time DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('inbox.html', messages=messages)

@app.route('/payment/<int:item_id>', methods=['GET'])
def payment(item_id):
    db = get_db_connection()
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        # Get the item
        item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            return "Item not found", 404

        if not item['is_closed']:
            return "Payment not allowed. Auction is still open.", 400

        # Get the highest bid
        highest_bid = db.execute(
            "SELECT * FROM bids WHERE item_id = ? ORDER BY amount DESC LIMIT 1",
            (item_id,)
        ).fetchone()

        if not highest_bid or highest_bid['bidder_id'] != user_id:
            return "You are not the winning bidder", 403

        # Check for existing payment
        existing_payment = db.execute(
            "SELECT * FROM payments WHERE item_id = ? AND buyer_id = ?",
            (item_id, user_id)
        ).fetchone()

        if existing_payment:
            return redirect(url_for('payment_info', item_id=item_id))

        # Insert new payment
        db.execute(
            "INSERT INTO payments (item_id, buyer_id, seller_id, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                item_id,
                user_id,
                item['user_id'],
                highest_bid['amount'],
                datetime.now().isoformat()
            )
        )
        db.commit()

        return redirect(url_for('payment_info', item_id=item_id))

    finally:
        db.close()

@app.route('/payment_info/<int:item_id>', methods=['GET'])
def payment_info(item_id):
    db = get_db_connection()
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        # Get the item
        item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            return "Item not found", 404

        # Get payment info for the current user and item
        payment = db.execute(
            "SELECT * FROM payments WHERE item_id = ? AND buyer_id = ?",
            (item_id, user_id)
        ).fetchone()

        if not payment:
            return "No payment found for this item", 404

        # Get the seller info
        seller = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (item['user_id'],)
        ).fetchone()

        if not seller:
            return "Seller not found", 404

        return render_template('payment_info.html', item=item, payment=payment, seller=seller)

    finally:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5050)))
