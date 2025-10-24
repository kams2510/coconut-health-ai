# app.py
import io
import sqlite3
import requests
from collections import Counter
from PIL import Image
from flask import Flask, render_template, request

from ultralytics import YOLO

app = Flask(__name__)
DB_PATH = 'database/recommendations.db'

# --- MODEL LOADING (Load Once at Startup) ---
model = YOLO('models/best.pt')
print("✅ YOLOv8 model loaded successfully.")

# --- CORE APPLICATION ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    
    if 'file' not in request.files or request.files['file'].filename == '':
        return render_template('result.html', error='No file selected.')

    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    
    weather_data = None
    if lat and lon:
        # NOTE: Remember to keep your API key private in a real-world project
        api_key = '30b102ac004c7b9889e2fffc0d36d4fe' 
        weather_data = get_weather_data(lat, lon, api_key)
        
    weather_condition = weather_data['condition'] if weather_data else "Any"

    file = request.files['file']
    try:
        img = Image.open(io.BytesIO(file.read()))
        # Set a confidence threshold for predictions
        results = model(img, conf=0.25) 
        
        processed_detections = []
        for result in results:
            for box in result.boxes.cpu().numpy():
                class_name = result.names[int(box.cls[0])]
                confidence = float(box.conf[0])
                disease, severity = ('unknown', 'default')
                parts = class_name.split('_')
                if len(parts) > 1 and parts[1] in ['mild', 'moderate', 'severe']:
                    disease, severity = parts[0], parts[1]
                else:
                    disease = class_name
                
                recommendation = get_recommendation(disease, severity, weather_condition)
                detection_data = {
                    'class_name': class_name,
                    'confidence_percent': int(confidence * 100),
                    'recommendation': recommendation['text'],
                    'risk_score': recommendation['risk'],
                    'weather': weather_data
                }
                processed_detections.append(detection_data)
                save_to_history(detection_data)
        
        return render_template('result.html', detections=processed_detections)
    except Exception as e:
        print(f"❌ Error during prediction: {e}")
        return render_template('result.html', error=f'An error occurred: {e}')

@app.route('/history')
def history():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history ORDER BY timestamp DESC")
        history_records = cursor.fetchall()
        
        detection_names = [record['detected_class'] for record in history_records]
        detection_counts = Counter(detection_names)
        chart_labels = list(detection_counts.keys())
        chart_data = list(detection_counts.values())
        
        conn.close()
        return render_template('history.html', records=history_records, chart_labels=chart_labels, chart_data=chart_data)
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        return "Error loading history page."

# --- HELPER FUNCTIONS ---
def get_weather_data(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        weather_condition, temp, humidity = "Any", data['main']['temp'], data['main']['humidity']
        if humidity > 85: weather_condition = "High Humidity"
        elif temp > 32: weather_condition = "High Temp"
        return {'condition': weather_condition, 'temp': temp, 'humidity': humidity}
    except requests.exceptions.RequestException as e:
        print(f"Weather API error: {e}")
        return None

def get_recommendation(disease_name, severity, weather_condition):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT recommendation_text, risk_score FROM advice WHERE disease_name=? AND severity=? AND weather_condition=?"
    cursor.execute(query, (disease_name, severity, weather_condition))
    result = cursor.fetchone()
    if not result:
        cursor.execute(query, (disease_name, severity, 'Any'))
        result = cursor.fetchone()
    conn.close()
    return {'text': result[0], 'risk': result[1]} if result else {'text': 'No generic advice found. Consult an expert.', 'risk': 'Unknown'}

def save_to_history(detection_data):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO history (detected_class, confidence, risk_score, recommendation_given)
        VALUES (?, ?, ?, ?)
        ''', (
            detection_data['class_name'],
            detection_data['confidence_percent'] / 100.0,
            detection_data['risk_score'],
            detection_data['recommendation']
        ))
        conn.commit()
        conn.close()
        print("✅ Saved to history.")
    except Exception as e:
        print(f"❌ Failed to save to history: {e}")

# --- RUN THE APPLICATION ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)