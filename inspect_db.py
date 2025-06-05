import sqlite3

conn = sqlite3.connect("support_bot.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Таблицы:", tables)

for table in tables:
    print(f"\nСодержимое таблицы {table[0]}:")
    rows = cursor.execute(f"SELECT * FROM {table[0]}").fetchall()
    for row in rows:
        print(row)

conn.close()
