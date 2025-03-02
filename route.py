from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg
from datetime import datetime, timedelta

app = Flask(__name__)

# Firebase credentials
cred = credentials.Certificate("adminsdk.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://agrosangam-57b8a-default-rtdb.firebaseio.com"
})

def fetch_last_1hr_data():
    """Fetch the last 1 hour of data from Firebase."""
    ref = db.reference("/sensor_data")
    current_time = datetime.now()
    start_time = current_time - timedelta(hours=1)
    
    data = ref.get()
    if not data:
        print("No data found in Firebase!")
        return pd.DataFrame()
    
    sensor_records = []
    for key, record in data.items():
        record_time = datetime.fromtimestamp(record["timestamp"] / 1000)  # Convert milliseconds to datetime
        if start_time <= record_time <= current_time:
            record["timestamp"] = record_time  # Convert timestamp to datetime
            sensor_records.append(record)
    
    if not sensor_records:
        print("No data available for the last 1 hour!")
        return pd.DataFrame()
    
    df = pd.DataFrame(sensor_records)
    df.sort_values(by="timestamp", inplace=True)  # Ensure correct time order
    return df

def train_ar_model(df, target_column, lags=5):
    """Trains an AutoRegressive (AR) model and forecasts salinity for the next 1 hour (60 minutes)."""
    series = df.set_index("timestamp")[target_column]  # Set time as index
    
    model = AutoReg(series, lags=lags).fit()  # Fit AR model
    forecast = model.predict(start=len(series), end=len(series) + 59)  # Predict next 60 min
    
    forecast_index = pd.date_range(df["timestamp"].iloc[-1] + timedelta(minutes=1), periods=60, freq='T')  # Future timestamps
    forecast_series = pd.Series(forecast.values, index=forecast_index)
    
    return model, forecast_series

@app.route('/forecast', methods=['GET'])
def forecast():
    df = fetch_last_1hr_data()  # Fetch data from Firebase
    
    if df.empty:
        return jsonify({"message": "No sufficient data to train the model!"})
    
    target_column = "salinity"  # Forecasting Salinity
    model, forecast = train_ar_model(df, target_column)
    
    # Prepare the response data
    forecast_data = forecast.to_dict()

    return jsonify(forecast_data)

if __name__ == "__main__":
    app.run(debug=True)
