import sqlite3

# Connect to your database
conn = sqlite3.connect('database.db')  # or retradehub.db if you're using that one
cursor = conn.cursor()

# Delete all rows from items table
cursor.execute('DELETE FROM items')

# Save changes and close connection
conn.commit()
conn.close()

print("All items deleted successfully!")
