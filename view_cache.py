import sqlite3, json;
conn = sqlite3.connect('weather_cache.db');
cursor = conn.cursor();
cursor.execute('SELECT city, timestamp, substr(data, 1, 100) FROM weather_data');
print('\n'.join(str(row) for row in cursor.fetchall()));
conn.close()
