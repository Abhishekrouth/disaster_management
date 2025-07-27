from flask import Flask, render_template, request, jsonify
import requests
from haversine import haversine
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re
import ast

load_dotenv()

app = Flask(__name__)

gemini_api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_api_key)

model = genai.GenerativeModel("gemini-1.5-flash")

def get_beaches_from_gemini(country):
    prompt = f"""
    Give me a comprehensive list of all major beaches in {country} with their name, latitude, and longitude.
    Include popular, famous, and well-known beaches from different regions/states/provinces of {country}.
    Provide at least 15-20 beaches if the country has that many coastal areas.
    Return the response strictly as a Python list of dictionaries like:
    [
        {{ "name": "Beach Name", "lat": 12.34, "lon": 56.78 }},
        ...
    ]
    Do not include any code blocks, comments, or extra text. Only return the list.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        print("GEMINI RAW RESPONSE TEXT >>>")
        print(text)
        
        text = re.sub(r'```json\s*\n?', '', text)
        text = re.sub(r'```python\s*\n?', '', text)
        text = re.sub(r'```\s*\n?', '', text)
        text = re.sub(r'\n?```', '', text)
        
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if (line and 
                not line.startswith('print(') and 
                not line.startswith('beaches =') and 
                not line.startswith('#') and
                line != 'print(beaches)'):
                filtered_lines.append(line)
        
        text = '\n'.join(filtered_lines)
        
        if 'beaches = [' in text:
            start_idx = text.find('[')
            end_idx = text.rfind(']') + 1
            text = text[start_idx:end_idx]
        text = text.strip()
        
        print("PROCESSED TEXT >>>")
        print(text)
        beaches = ast.literal_eval(text)
        return beaches
        
    except Exception as e:
        print("Gemini error:", e)
        print("Failed to parse text:", text)
        return []


def get_nasa_disasters():
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=7"
    r = requests.get(url)
    return r.json().get("events", [])

def check_disasters_near(lat, lon):
    alerts = []
    for event in get_nasa_disasters():
        for g in event['geometry']:
            ev_lat, ev_lon = g['coordinates'][1], g['coordinates'][0]
            dist = haversine((lat, lon), (ev_lat, ev_lon))
            if dist <= 200:
                alerts.append(event['title'])
    return alerts

@app.route("/")
def home():
    with open("data/countries.txt", "r") as f:
        countries = [line.strip() for line in f if line.strip()]
    return render_template("index.html", countries=countries)

@app.route("/get_beaches", methods=["POST"])
def get_beaches():
    country = request.form['country']
    beaches = get_beaches_from_gemini(country)
    if not beaches:
        return render_template("beaches.html", country=country, beaches=[])
    return render_template("beaches.html", country=country, beaches=beaches)

@app.route("/check_alert", methods=["POST"])
def check_alert():
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    beach_name = request.form['beach']
    alerts = check_disasters_near(lat, lon)
    return render_template("result.html", beach=beach_name, alerts=alerts)

if __name__ == '__main__':
    app.run(debug=True)
