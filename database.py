import sqlite3

# Connect to the database (creates database.db if it doesn't exist)
conn = sqlite3.connect('database.db')

# Create users table
conn.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    phonepe_id TEXT,
    is_seller BOOLEAN NOT NULL DEFAULT 0,
    joined_date TEXT DEFAULT CURRENT_TIMESTAMP
);
''')

# Create items table
conn.execute('''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    user_id INTEGER,
    photo_filename TEXT,
    highest_bid REAL DEFAULT 0,
    highest_bid_user_id INTEGER,
    auction_end_time TEXT,
    is_closed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (highest_bid_user_id) REFERENCES users(id)
);
''')

# Create bids table
conn.execute('''
CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    bidder_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    bid_time TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (bidder_id) REFERENCES users(id)
);
''')

# Create chats table
conn.execute('''
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);
''')

# Create messages table
conn.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);
''')

# Create ideas table
conn.execute('''
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    contributor_id INTEGER,
    posted_at TEXT NOT NULL,
    FOREIGN KEY (contributor_id) REFERENCES users(id)
);
''')

# Create transactions table (keep only one correct definition)
conn.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER,
    item_id INTEGER,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    transaction_time TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);
''')

# Create payments table
conn.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    buyer_id INTEGER,
    seller_id INTEGER,
    amount REAL,
    timestamp TEXT
);
''')

# Commit and close
conn.commit()
conn.close()

print("✅ Database and tables created successfully.")
