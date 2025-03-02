from app import db_user, db_dashboard

# User Model (Primary Database)
class User(db_user.Model):
    id = db_user.Column(db_user.Integer, primary_key=True)
    username = db_user.Column(db_user.String(100), nullable=False)
    role = db_user.Column(db_user.String(50), nullable=False)  # 'Farmer' or 'Consumer'
    email = db_user.Column(db_user.String(150), unique=True, nullable=False)
    password = db_user.Column(db_user.String(60), nullable=False)

# Crop Model (Secondary Database)
class Crop(db_dashboard.Model):
    __bind_key__ = 'dashboard'  # Bind to secondary database
    id = db_dashboard.Column(db_dashboard.Integer, primary_key=True)
    farmer_id = db_dashboard.Column(db_dashboard.Integer, nullable=False)
    name = db_dashboard.Column(db_dashboard.String(100), nullable=False)
    price_per_ton = db_dashboard.Column(db_dashboard.Float, nullable=False)
    quantity_available = db_dashboard.Column(db_dashboard.Integer, nullable=False)

# Order Model (Secondary Database)
class Order(db_dashboard.Model):
    __bind_key__ = 'dashboard'  # Bind to secondary database
    id = db_dashboard.Column(db_dashboard.Integer, primary_key=True)
    consumer_id = db_dashboard.Column(db_dashboard.Integer, nullable=False)
    farmer_id = db_dashboard.Column(db_dashboard.Integer, nullable=False)
    crop_name = db_dashboard.Column(db_dashboard.String(100), nullable=False)
    quantity = db_dashboard.Column(db_dashboard.Integer, nullable=False)
    total_price = db_dashboard.Column(db_dashboard.Float, nullable=False)
    delivery_address = db_dashboard.Column(db_dashboard.String(255), nullable=False)
    agreement_pdf = db_dashboard.Column(db_dashboard.String(255), nullable=True)
