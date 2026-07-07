import sqlite3
conn = sqlite3.connect('signly.db')
c = conn.cursor()
c.execute('SELECT username, is_active, is_deleted FROM users WHERE username="Quason"')
print(c.fetchone())
conn.close()
