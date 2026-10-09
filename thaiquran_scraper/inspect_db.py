import sqlite3

conn = sqlite3.connect('H:/gits/thai-quran-app/assets/quran_offline.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print("Tables:", tables)

for t in tables:
    cursor.execute(f"SELECT count(*) FROM {t}")
    cnt = cursor.fetchone()[0]
    cursor.execute(f"PRAGMA table_info({t})")
    cols = [c[1] for c in cursor.fetchall()]
    print(f"  {t} ({cnt} rows): {cols}")
