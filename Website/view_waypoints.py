import sqlite3
import os

# === Datenbankverbindung ===
db_path = "orders.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# === Daten abrufen ===
rows = conn.execute("SELECT * FROM extraorder_waypoints ORDER BY id DESC").fetchall()

# === Ausgabe-Ordner vorbereiten ===
output_dir = os.path.expanduser("~/maturaarbeit/final_test")
os.makedirs(output_dir, exist_ok=True)

# === Ziel-Datei ===
output_file = os.path.join(output_dir, "waypoints.txt")

# === Schreiben in Textdatei ===
with open(output_file, "w", encoding="utf-8") as f:
    if not rows:
        f.write("Keine Einträge in der Tabelle 'extraorder_waypoints' gefunden.\n")
    else:
        for row in rows:
            f.write(str(dict(row)) + "\n")

# === Aufräumen ===
conn.close()

print(f"Daten erfolgreich gespeichert in: {output_file}")
