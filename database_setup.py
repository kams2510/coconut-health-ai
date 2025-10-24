# database_setup.py
import sqlite3
import os

DB_PATH = os.path.join('database', 'recommendations.db')
os.makedirs('database', exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("Database connected.")

# Drop old tables for a clean slate
cursor.execute("DROP TABLE IF EXISTS advice")
cursor.execute("DROP TABLE IF EXISTS history")
print("Old tables dropped.")

# --- Create history table (without user_id) ---
cursor.execute('''
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    detected_class TEXT NOT NULL,
    confidence REAL NOT NULL,
    risk_score TEXT NOT NULL,
    recommendation_given TEXT NOT NULL
)
''')
print("Table 'history' created.")

# --- Create and populate advice table ---
cursor.execute('''
CREATE TABLE advice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_name TEXT NOT NULL, severity TEXT,
    weather_condition TEXT NOT NULL, 
    recommendation_text TEXT NOT NULL, risk_score TEXT NOT NULL
)
''')
recommendations = [
    # Generic/Fallback rules
    ('wcwld', 'mild', 'Any', 'Apply balanced fertilizer with extra Potassium (K). Monitor weekly.', 'Low'),
    ('wcwld', 'moderate', 'Any', 'Remove/destroy affected leaves. Apply recommended fungicides.', 'Medium'),
    ('wcwld', 'severe', 'Any', 'URGENT: Isolate and consider culling the palm to prevent spread. Seek expert help.', 'High'),
    ('caterpillar_infestation', 'default', 'Any', 'Spray a neem-based insecticide. Introduce natural predators.', 'Medium'),
    
    # Weather-specific rules
    ('wcwld', 'mild', 'High Humidity', 'High humidity (>85%) promotes fungal growth. Ensure proper air circulation and consider a preventative copper-based fungicide spray.', 'Medium'),
    ('wcwld', 'mild', 'High Temp', 'High temperatures (>32°C) cause heat stress, worsening symptoms. Ensure consistent irrigation and apply mulch to keep roots cool.', 'Medium')
]
cursor.executemany('INSERT INTO advice (disease_name, severity, weather_condition, recommendation_text, risk_score) VALUES (?, ?, ?, ?, ?)', recommendations)
print("Table 'advice' populated with weather-specific rules.")

conn.commit()
conn.close()
print("Database setup complete.")