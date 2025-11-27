import sqlite3
conn = sqlite3.connect('admin/data/drum_training.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(egmd_midi_features)')
columns = [row[1] for row in cur.fetchall()]
print('Current schema columns:')
for col in columns:
    print(f'  - {col}')
conn.close()
