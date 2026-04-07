from db import get_connection

conn = get_connection()
print("Connected successfully!")
conn.close()