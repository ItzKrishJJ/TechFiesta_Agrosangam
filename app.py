import os
from flask import Flask, jsonify, render_template, redirect, session, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import DateField, StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from fpdf import FPDF
from flask import send_from_directory
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import sqlite3
import numpy as np
import torch
import torchvision
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import joblib
import os
import groq
from geopy.distance import geodesic
import firebase_admin
from firebase_admin import credentials, db
import bcrypt
from geopy.distance import geodesic  # ✅ Calculate distances between farmers
from flask_login import LoginManager
from firebase_admin import db as firebase_db  

# Initialize app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Load trained model and preprocessing objects
rmodel = joblib.load('ml/recommend/crop_recommendation_model.pkl')
rlabel_encoder = joblib.load('ml/recommend/label_encoder.pkl')
rscaler = joblib.load('ml/recommend/scaler.pkl')
GROQ_API_KEY = "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"
client = groq.Client(api_key=GROQ_API_KEY)


# API Configuration
API_URL = "https://api.example.com/resource/9ef84268-d588-465a-a308-a864a43d0070"
API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"


# Set up the database paths
app_db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
dash_db_path = os.path.join(os.getcwd(), 'instance', 'dashboard.db')
os.makedirs(os.path.dirname(app_db_path), exist_ok=True)
os.makedirs(os.path.dirname(dash_db_path), exist_ok=True)

# Configure databases
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app_db_path}"
app.config['SQLALCHEMY_BINDS'] = {
    'dashboard': 'sqlite:///dashboard.db'
}

app.config['SQLALCHEMY_BINDS'] = {
    'dashboard': f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'dashboard.db')}"
}

# ✅ Initialize Firebase
cred = credentials.Certificate("agrosangam-57b8a-firebase-adminsdk-fbsvc-7e17b1d5cb.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://agrosangam-57b8a-default-rtdb.firebaseio.com'
})


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Use session.get() instead of query.get()


# Models
class User(db.Model, UserMixin):
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    aadhar_no = db.Column(db.String(12), unique=True, nullable=False)
    phone_no = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Farmer or Consumer
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    latitude = db.Column(db.Float, nullable=True)  # ✅ Added GPS location fields
    longitude = db.Column(db.Float, nullable=True)
    
    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True  # ✅ Required for Flask-Login

    @property
    def is_active(self):
        return True  # ✅ Required for Flask-Login

    @property
    def is_anonymous(self):
        return False  # ✅ Required for Flask-Login


login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # ✅ Fetch user properly

class Crop(db.Model):
    __bind_key__ = 'dashboard'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price_per_ton = db.Column(db.Float, nullable=False)
    quantity_available = db.Column(db.Integer, nullable=False)
    State = db.Column(db.String(50))
    District = db.Column(db.String(50))
    harvest_date = db.Column(db.Date)  # Add Harvest Date
    grade = db.Column(db.String(1))  # Add Crop Grade (A, B, C, D)
    category = db.Column(db.String(20))  # Add Category Column
    farmer_address = db.Column(db.String(255), nullable=True)  # New Column



class Order(db.Model):
    __bind_key__ = 'dashboard'  # Ensures it connects to dashboard.db
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer)
    farmer_id = db.Column(db.Integer)
    crop_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    agreement_pdf = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    feedback = db.Column(db.Text, nullable=True)  # New feedback column


    def __repr__(self):
        return f"<Order {self.id}>"



# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    aadhar_no = StringField('Aadhar Number', validators=[
        DataRequired(), Length(min=12, max=12), Regexp(r'^\d{12}$', message='Aadhar number must be 12 digits.')
    ])
    phone_no = StringField('Phone Number', validators=[
        DataRequired(), Regexp(r'^\d{10}$', message='Phone number must be 10 digits.')
    ])
    role = SelectField('Role', choices=[('Farmer', 'Farmer'), ('Consumer', 'Consumer')], validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    captcha = StringField('Captcha: What is 3 + 4?', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered.')

    def validate_aadhar_no(self, aadhar_no):
        user = User.query.filter_by(aadhar_no=aadhar_no.data).first()
        if user:
            raise ValidationError('Aadhar number is already registered.')

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
class AddCropForm(FlaskForm):
    State = SelectField('State', choices=[], validators=[DataRequired()])
    District = SelectField('District', choices=[], validators=[DataRequired()])
    crop = SelectField('Crop', choices=[
        ('Wheat', 'Wheat'), ('Rice', 'Rice'), ('Corn', 'Corn'),
        ('Cotton', 'Cotton'), ('Brinjal', 'Brinjal'), ('Banana', 'Banana'),
        ('Turmeric', 'Turmeric'), ('Tomato', 'Tomato'), ('Soyabean', 'Soyabean'),
        ('Cauliflower', 'Cauliflower')
    ], validators=[DataRequired()])
    price_per_ton = StringField('Price Per Ton', validators=[DataRequired()], render_kw={"readonly": True})
    quantity_available = StringField('Quantity Available', validators=[DataRequired()])
    harvest_date = DateField('Harvest Date', format='%Y-%m-%d', validators=[DataRequired()])  # New field
    grade = SelectField('Grade', choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], validators=[DataRequired()])  # New field



# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    # Debugging: Print form errors (if any)
    print("Form validation errors:", form.errors)

    if form.validate_on_submit():
        # Debugging: Print submitted form data
        print("Form Data Submitted:", form.data)

        # CAPTCHA validation
        if form.captcha.data.strip() != "7":
            flash('Incorrect CAPTCHA answer.', 'danger')
            return render_template('register.html', form=form)

        try:
            # Hash the password
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

            # Check for duplicate Aadhaar or email
            existing_user_email = User.query.filter_by(email=form.email.data).first()
            existing_user_aadhar = User.query.filter_by(aadhar_no=form.aadhar_no.data).first()

            if existing_user_email:
                flash('Email is already registered. Please use a different email.', 'danger')
                return render_template('register.html', form=form)

            if existing_user_aadhar:
                flash('Aadhaar number is already registered. Please use a different Aadhaar.', 'danger')
                return render_template('register.html', form=form)

            # Create the user
            user = User(
                username=form.username.data,
                aadhar_no=form.aadhar_no.data,
                phone_no=form.phone_no.data,
                role=form.role.data,
                email=form.email.data,
                password=hashed_password
            )

            # Add user to the database
            db.session.add(user)
            db.session.commit()

            # Success message and redirect
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            # Rollback in case of an error
            db.session.rollback()
            print(f"Error during registration: {e}")  # Debugging: Log the error
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('register.html', form=form)


# ✅ Ensure Firebase is initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-adminsdk.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://agrosangam-57b8a-default-rtdb.firebaseio.com/'
    })


# ✅ User Model
bcrypt = Bcrypt()  # ✅ Ensure Flask

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if request.method == "GET":
        return render_template("login.html", form=form)

    email = request.form.get("email")
    password = request.form.get("password")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")

    user = User.query.filter_by(email=email).first()  # ✅ Fetch user from SQLAlchemy

    if user and bcrypt.check_password_hash(user.password, password):  # ✅ Corrected bcrypt usage
        login_user(user)
        session["user_id"] = user.id

        # ✅ If farmer, update location in SQLAlchemy & Firebase
        if user.role == "Farmer":
            session["is_farmer"] = True
            if latitude and longitude:
                try:
                    # ✅ Update SQLite Database
                    user.latitude = float(latitude)
                    user.longitude = float(longitude)
                    db.session.commit()

                    # ✅ Update Firebase Live Location
                    db.reference(f'farmers/{user.id}/location').set({"latitude": latitude, "longitude": longitude})
                    print(f"✅ Farmer {user.id} location updated in Firebase: {latitude}, {longitude}")
                except Exception as e:
                    print(f"❌ Firebase Location Update Failed: {e}")

        flash("Login successful!", "success")
        return redirect(url_for("home"))

    flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


from datetime import datetime

@app.route('/farmer_dashboard', methods=['GET', 'POST'])
@login_required
def farmer_dashboard():
    if current_user.role != 'Farmer':
        return redirect(url_for('home'))

    form = AddCropForm()

    # Provide dynamic options for state and district if required
    form.State.choices = [('Maharashtra', 'Maharashtra'), ('Gujarat', 'Gujarat'), ('Punjab', 'Punjab')]
    form.District.choices = [('Nashik', 'Nashik'), ('Dhule', 'Dhule'), ('Pune', 'Pune'), ('Mumbai', 'Mumbai'),
                              ('Nagpur', 'Nagpur'), ('Surat', 'Surat'), ('Amritsar', 'Amritsar')]

    category_mapping = {
        "Banana": "fruits",
        "Brinjal": "vegetables",
        "Cauliflower": "vegetables",
        "Tomato": "vegetables",
        "Turmeric": "pulses",
        "Soyabean": "pulses",
        "Wheat": "grains",
        "Rice": "grains",
        "Corn": "grains",
        "Cotton": "grains"
    }

    if request.method == 'POST' and form.validate_on_submit():
        name = form.crop.data.strip().title()  # Normalize crop name
        price_per_ton = float(form.price_per_ton.data)
        quantity_available = int(form.quantity_available.data)
        State = form.State.data
        District = form.District.data
        harvest_date = datetime.strptime(request.form['harvest_date'], '%Y-%m-%d').date()
        grade = request.form['grade']
        category = category_mapping.get(name, "others")  # Assign category
        farmer_address = request.form['farmer_address']  # New Field

        # Add crop to the database
        new_crop = Crop(
            farmer_id=current_user.id,
            name=name,
            price_per_ton=price_per_ton,
            quantity_available=quantity_available,
            State=State,
            District=District,
            harvest_date=harvest_date,
            grade=grade,
            category=category,  # Ensure this column exists
            farmer_address=farmer_address
        )
        db.session.add(new_crop)

        try:
            db.session.commit()
            flash('Crop added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error occurred: {e}", 'danger')

        return redirect(url_for('farmer_dashboard'))

    crops = Crop.query.filter_by(farmer_id=current_user.id).all()
    return render_template('farmer_dashboard.html', crops=crops, form=form)


# Delete and update crop
@app.route('/delete_crop/<int:crop_id>', methods=['POST'])
@login_required
def delete_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)

    # Ensure only the owner can delete the crop
    if crop.farmer_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('farmer_dashboard'))

    try:
        db.session.delete(crop)
        db.session.commit()
        flash("Crop deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting crop: {str(e)}", "danger")

    return redirect(url_for('farmer_dashboard'))

from datetime import datetime

@app.route('/update_crop/<int:crop_id>', methods=['GET', 'POST'])
@login_required
def update_crop(crop_id):
    if current_user.role != 'Farmer':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    crop = Crop.query.get_or_404(crop_id)

    if crop.farmer_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    if request.method == 'POST':
        crop.name = request.form['name']
        crop.price_per_ton = float(request.form['price_per_ton'])
        crop.quantity_available = int(request.form['quantity_available'])
        
        # Convert harvest_date to a Python date object
        crop.harvest_date = datetime.strptime(request.form['harvest_date'], '%Y-%m-%d').date()

        crop.grade = request.form['grade']

        db.session.commit()
        flash('Crop details updated successfully!', 'success')
        return redirect(url_for('farmer_dashboard'))

    return render_template('update_crop.html', crop=crop)

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    crop_id = request.form['crop_id']
    new_quantity = int(request.form['quantity'])
    
    if 'cart' in session:
        for item in session['cart']:
            if item['crop_id'] == int(crop_id):
                item['quantity'] = new_quantity
                item['total_price'] = new_quantity * item['price_per_ton']
                break
        session.modified = True
    
    flash('Cart updated successfully!', 'success')
    return redirect(url_for('cart'))


@app.route('/submit_feedback/<int:order_id>', methods=['GET', 'POST'])
@login_required
def submit_feedback(order_id):
    order = Order.query.get_or_404(order_id)

    if request.method == 'POST':
        if order.consumer_id != current_user.id:
            flash("Unauthorized action!", "danger")
            return redirect(url_for('order_history'))

        feedback_text = request.form['feedback']
        order.feedback = feedback_text
        db.session.commit()
        flash("Feedback submitted successfully!", "success")
        return redirect(url_for('order_history'))

    return render_template('submit_feedback.html', order_id=order_id)



@app.route('/fetch_price', methods=['POST'])
def fetch_price():
    data = request.get_json()
    state = data.get('state')
    district = data.get('district')
    crop = data.get('crop')
    grade = data.get('grade')
    
    api_url = f"{API_URL}?api-key={API_KEY}&format=json&filters[state.keyword]={state}&filters[district]={district}&filters[commodity]={crop}&filters[grade]={grade}"
    
    response = request.get(api_url)
    if response.status_code == 200:
        price_data = response.json()
        if price_data and len(price_data) > 0:
            return jsonify({'price': price_data[0]['current_price']})
    return jsonify({'error': 'No price data found for the selected criteria'}), 404

@app.route('/consumer_track_order/<int:order_id>')
@login_required
def consumer_track_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash("Order not found!", "danger")
        return redirect(url_for("order_history"))

    return render_template("consumer_track_order.html", order_id=order.id)


@app.route('/consumer_dashboard')
@login_required
def consumer_dashboard():
    if current_user.role != 'Consumer':
        flash('Access denied. You are not authorized to view this page.', 'danger')
        return redirect(url_for('home'))
    
    # Add logic to fetch data for the consumer dashboard
    # For example, display available crops, cart items, etc.
    return render_template('consumer_dashboard.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('q', '')  # Get the search query from URL params
    # Process the query and return results
    return render_template('search_results.html', query=query)

@app.route('/view_crops', methods=['GET'])
@login_required
def view_crops():
    if current_user.role != 'Consumer':
        return redirect(url_for('home'))

    # Get the selected category from the request
    category = request.args.get('category', 'all')  

    # Fetch crops from the database based on category
    if category == 'all':
        crops = Crop.query.filter(Crop.quantity_available > 0).all()
    else:
        crops = Crop.query.filter(Crop.quantity_available > 0, Crop.category == category).all()

    # Fetch farmer details separately from app.db
    farmers = {user.id: user.username for user in User.query.all()}

    return render_template('view_crops.html', crops=crops, farmers=farmers, selected_category=category)

@app.route('/view_cart')
def view_cart():
    # Assuming you have a session or database to store cart items
    cart_item_count = len(current_user.cart)  # Example logic
    return render_template('your_template.html', cart_item_count=cart_item_count)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    crop_id = request.form['crop_id']
    quantity = int(request.form['quantity'])
    crop = Crop.query.get(crop_id)

    if crop and crop.quantity_available >= quantity:
        total_price = crop.price_per_ton * quantity

        # Store the cart in the session
        if 'cart' not in session:
            session['cart'] = []

        session['cart'].append({
            'crop_id': crop.id,
            'crop_name': crop.name,
            'price_per_ton': crop.price_per_ton,
            'quantity': quantity,
            'total_price': total_price,
            "farmer_id": crop.farmer_id,  # Store farmer_id in the cart
            "farmer_address": crop.farmer_address  # Store farmer's address
        })
        session.modified = True

        flash(f'{quantity} tons of {crop.name} added to your cart for ₹{total_price}.', 'success')
    else:
        flash('Insufficient quantity available.', 'danger')

    return redirect(url_for('view_crops'))

@app.route('/cart', methods=['GET'])
@login_required
def cart():
    return render_template('cart.html', cart=session.get('cart', []))


# @app.route('/cart', methods=['POST'])
# @login_required
# def cart():
#     crop_id = request.form['crop_id']
#     quantity = int(request.form['quantity'])
#     crop = Crop.query.get(crop_id)

#     if crop and crop.quantity_available >= quantity:
#         total_price = crop.price_per_ton * quantity
#         new_order = Order(
#             consumer_id=current_user.id,  # Store consumer ID
#             farmer_id=crop.farmer_id,  # Store farmer ID without FK constraint
#             crop_name=crop.name,
#             quantity=quantity,
#             total_price=total_price,
#             delivery_address=""
#         )

#         db.session.add(new_order)
#         db.session.commit()
#         flash(f'Order placed for {quantity} tons of {crop.name}. Awaiting farmer confirmation.', 'success')
#     else:
#         flash('Insufficient quantity available.', 'danger')

#     return redirect(url_for('view_crops'))





@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    crop_id = request.form['crop_id']
    
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['crop_id'] != int(crop_id)]
        session.modified = True
    
    flash('Item removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    try:
        cart = session.get('cart', [])

        if not cart:
            flash('Your cart is empty!', 'danger')
            return redirect(url_for('cart'))

        consumer_location = request.form.get('destination_address', '').strip()
        final_total_price = request.form.get('final_total_price', '').strip()

        # Validate Consumer Address
        if not consumer_location:
            flash("Please enter a valid consumer location!", "danger")
            return redirect(url_for('cart'))

        # Validate Total Price
        try:
            final_total_price = float(final_total_price)  # Ensure it's a valid float
        except ValueError:
            flash("Error calculating total price. Please try again!", "danger")
            return redirect(url_for('cart'))

        # Process order creation
        with db.session.begin_nested():
            for item in cart:
                crop = Crop.query.get(item['crop_id'])
                if not crop:
                    flash(f"Crop {item['crop_name']} not found!", "danger")
                    continue


                # Create order with correct farmer_id
                new_order = Order(
                    consumer_id=current_user.id,
                    farmer_id=crop.farmer_id,
                    crop_name=item['crop_name'],
                    quantity=item['quantity'],
                    total_price=final_total_price,  # Store final cost
                    delivery_address=consumer_location,
                    status="Pending"
                )
                db.session.add(new_order)

        db.session.commit()
        session.pop('cart', None)  # Clear cart after order is placed

        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_history'))

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('cart'))




@app.context_processor
def inject_pending_orders_count():
    if current_user.is_authenticated and current_user.role == 'Farmer':
        try:
            with db.session.connection(execution_options={"schema_translate_map": {"orders": "dashboard"}}):
                pending_orders_count = Order.query.filter_by(farmer_id=current_user.id, status="Pending").count()
        except Exception as e:
            print("Error fetching pending orders:", e)
            pending_orders_count = 0
    else:
        pending_orders_count = 0
    return dict(pending_orders_count=pending_orders_count)


@app.route('/redirect_user')
@login_required
def redirect_user():
    if current_user.role == "Farmer":
        return redirect(url_for('farmer_dashboard'))
    elif current_user.role == "Consumer":
        return redirect(url_for('view_crops'))
    else:
        return redirect(url_for('login'))  # Fallback if not logged in


@app.route('/pending_requests', methods=['GET'])
@login_required
def pending_requests():
    if current_user.role != 'Farmer':
        return redirect(url_for('home'))

    orders = Order.query.filter_by(farmer_id=current_user.id, status="Pending").all()
    consumers = {user.id: user.username for user in User.query.all()}
    farmers = {user.id: user.username for user in User.query.all()}
    
    return render_template('pending_requests.html', orders=orders, consumers=consumers, farmers=farmers)

@app.route('/accept_order/<int:order_id>', methods=['POST'])
@login_required
def accept_order(order_id):
    order = Order.query.get(order_id)
    
    if order and order.farmer_id == current_user.id:
        order.status = "Accepted"

        # Reduce Crop Quantity only when accepting the order
        crop = Crop.query.filter_by(name=order.crop_name, farmer_id=order.farmer_id).first()
        if crop and crop.quantity_available >= order.quantity:
            crop.quantity_available -= order.quantity
            
            # Remove crop if quantity becomes zero
            if crop.quantity_available == 0:
                db.session.delete(crop)

            db.session.commit()

            flash("Order accepted. Crop quantity updated.", "success")
        else:
            flash(f"Not enough {order.crop_name} available!", "danger")
            return redirect(url_for('pending_requests'))

        # Generate Agreement PDF
        pdf_file = generate_agreement(order)
        order.agreement_pdf = pdf_file
        db.session.commit()

        flash("Order accepted. Agreement generated.", "success")

    return redirect(url_for('pending_requests'))


@app.route('/reject_order/<int:order_id>', methods=['POST'])
@login_required
def reject_order(order_id):
    order = Order.query.get(order_id)
    if order and order.farmer_id == current_user.id:
        order.status = "Rejected"
        db.session.commit()
        flash("Order rejected.", "danger")
    return redirect(url_for('pending_requests'))

@app.route('/order_history')
@login_required
def order_history():
    if current_user.role == "Farmer":
        orders = Order.query.filter_by(farmer_id=current_user.id).all()
    else:
        orders = Order.query.filter_by(consumer_id=current_user.id).all()

    return render_template('order_history.html', orders=orders)


@app.route('/agreements/order_<int:order_id>.pdf')
@login_required  # Optional: Protect files from unauthorized access
def serve_agreement(order_id):
    agreements_dir = os.path.abspath("static/agreements")  # Get absolute path
    filename = f"order_{order_id}.pdf"  # Match filename format
    return send_from_directory(agreements_dir, filename)

@app.route("/track_order/<int:order_id>")
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Ensure only farmers can track orders
    if current_user.role != "Farmer":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("order_history"))

    return render_template("track_order.html", consumer_address=order.delivery_address,order=order)

@app.route('/collaborative_delivery/<int:order_id>')
def collaborative_delivery(order_id):
    order = Order.query.get(order_id)  # Fetch order from the database

    if not order:
        flash("Order not found!", "danger")
        return redirect(url_for('order_history'))  # Redirect if order does not exist

    return render_template('collaborative_delivery.html', order=order, consumer_address=order.delivery_address, farmer_id=order.farmer_id)

# ✅ Update farmer location in Firebase
@app.route('/update_farmer_location', methods=['POST'])
def update_farmer_location():
    try:
        data = request.json
        farmer_id = data.get('farmer_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not farmer_id or latitude is None or longitude is None:
            return jsonify({'error': 'Missing required data'}), 400

        # ✅ Update the farmer's location in `app.db`
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user 
            SET latitude = ?, longitude = ?
            WHERE id = ? AND role = 'Farmer'
        """, (latitude, longitude, farmer_id))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Farmer location updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ Find nearby farmers within 10 km for collaboration

# ✅ Connect to `app.db` & Fetch Nearby Farmers

from flask import request, jsonify
import firebase_admin
from geopy.distance import geodesic

# ✅ Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("agrosangam-57b8a-firebase-adminsdk-fbsvc-7e17b1d5cb.json")  # Replace with your actual Firebase credentials
    firebase_admin.initialize_app(cred, {"databaseURL": "https://agrosangam-57b8a-default-rtdb.firebaseio.com"})
    
@app.route("/check_nearby_farmers", methods=["POST"])
def check_nearby_farmers():
    try:
        data = request.get_json()
        print("📥 Received Request Data:", data)  # ✅ Debugging

        farmer_id = data.get("farmer_id")
        farmer_location = data.get("farmer_location")

        if not farmer_id or not farmer_location:
            return jsonify({"error": "Missing farmer_id or farmer_location"}), 400

        farmers_ref = firebase_db.reference("farmers")
        all_farmers = farmers_ref.get()

        print("📌 All Farmers Data from Firebase:", all_farmers)  # ✅ Debugging

        if not all_farmers:
            return jsonify({"error": "No farmers found"}), 404  # ✅ Return proper error

        matching_farmers = []
        for other_farmer_id, farmer_data in all_farmers.items():
            if other_farmer_id == farmer_id:
                continue  # ✅ Skip self

            other_location = farmer_data.get("location")
            if not other_location:
                print(f"⚠ Farmer {other_farmer_id} has no location data.")  # ✅ Debugging
                continue  

            distance = geodesic(
                (farmer_location["latitude"], farmer_location["longitude"]),
                (other_location["latitude"], other_location["longitude"])
            ).km

            if distance <= 10:
                matching_farmers.append({
                    "farmer_id": other_farmer_id,
                    "latitude": other_location["latitude"],
                    "longitude": other_location["longitude"]
                })

        print("✅ Found Nearby Farmers:", matching_farmers)  # ✅ Debugging Output
        return jsonify({"matching_farmers": matching_farmers}), 200

    except Exception as e:
        print(f"❌ Server Error in check_nearby_farmers: {e}")
        return jsonify({"error": str(e)}), 500
            
# ✅ Send collaboration request
@app.route('/send_collab_request', methods=['POST'])
def send_collab_request():
    try:
        data = request.json
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        order_id = data.get('order_id')

        if not sender_id or not receiver_id or not order_id:
            return jsonify({'error': 'Missing data'}), 400

        collab_ref = firebase_db.reference(f'collaboration_requests/{receiver_id}/{sender_id}')
        collab_ref.set({'status': 'Pending', 'order_id': order_id})

        print(f"✅ Collaboration request sent from {sender_id} to {receiver_id}")
        return jsonify({'message': 'Collaboration request sent'}), 200

    except Exception as e:
        print(f"❌ Error sending collaboration request: {e}")
        return jsonify({'error': str(e)}), 500


def generate_agreement(order):
    consumer = User.query.get(order.consumer_id)
    farmer = User.query.get(order.farmer_id)

    # Define directory path for agreements
    agreements_dir = os.path.join("static", "agreements")

    # Ensure the directory exists
    if not os.path.exists(agreements_dir):
        os.makedirs(agreements_dir)

    # Correct file path using forward slashes for Flask compatibility
    pdf_filename = f"order_{order.id}.pdf"
    pdf_file_path = os.path.join(agreements_dir, pdf_filename).replace("\\", "/")  # Fix for Windows paths
    pdf_url_path = f"/static/agreements/{pdf_filename}"  # Web-accessible URL

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Farm-to-Table Agreement", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Farmer: {farmer.username}", ln=True)
    pdf.cell(200, 10, txt=f"Consumer: {consumer.username}", ln=True)
    pdf.cell(200, 10, txt=f"Crop: {order.crop_name}", ln=True)
    pdf.cell(200, 10, txt=f"Quantity: {order.quantity} tons", ln=True)
    pdf.cell(200, 10, txt=f"Delivery Address: {order.delivery_address}", ln=True)

    # Save the PDF file
    pdf.output(pdf_file_path)

    return pdf_url_path  # Return the URL path instead of file path



@app.route('/recommend_crop')
def recommend_crop_page():
    return render_template('recommend_crop.html')

@app.route('/predict_yield')
def yield_prediction_page():
    return render_template('predict_yield.html')

@app.route('/freshness_test')
def freshness_test_page():
    return render_template('freshness_test.html')

@app.route('/ai-chatbot-page')
def ai_chatbot_page():
    return render_template('ai_chatbot_page.html')

@app.route('/recommend_crop', methods=['POST'])
def recommend_crop():
    try:
        data = request.get_json()
        
        # Extract features from the request
        features = np.array([
            data['N'], data['P'], data['K'], data['temperature'],
            data['humidity'], data['ph'], data['rainfall']
        ]).reshape(1, -1)
        
        # Scale the input features
        features_scaled = rscaler.transform(features)
        
        # Predict crop
        prediction = rmodel.predict(features_scaled)
        crop = rlabel_encoder.inverse_transform(prediction)[0]
        
        return jsonify({'recommended_crop': crop})
    except Exception as e:
        return jsonify({'error': str(e)})


# Load the trained model and preprocessing objects
pmodel = joblib.load("ml/predict/crop_yield_model.pkl")
pencoder = joblib.load("ml/predict/crop_yield_encoder.pkl")
pscaler = joblib.load("ml/predict/crop_yield_scaler.pkl")

# Categorical and numerical columns
categorical_cols = ["Crop", "Season", "State"]
numerical_cols = ["Crop_Year", "Area", "Production", "Annual_Rainfall", "Fertilizer", "Pesticide"]

@app.route("/predict_yield", methods=["POST"])
def predict_yield():
    try:
        data = request.json
        
        # Extract categorical and numerical values
        X_cat = pencoder.transform([[data[col] for col in categorical_cols]])
        X_num = pscaler.transform([[data[col] for col in numerical_cols]])
        
        # Concatenate transformed features
        X_input = np.hstack((X_cat, X_num))
        
        # Make prediction
        prediction = pmodel.predict(X_input)[0]
        
        return jsonify({"predicted_yield": prediction})
    
    except Exception as e:
        return jsonify({"error": str(e)})


device = 'cuda' if torch.cuda.is_available() else 'cpu'
class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.alpha = 0.7
        
        self.base = torchvision.models.resnet18(pretrained=True)
        
        for param in list(self.base.parameters())[:-15]:
            param.requires_grad = False

        self.base.classifier = nn.Sequential()
        self.base.fc = nn.Sequential()
        
        self.block1 = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
        )
        
        self.block2 = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 9)
        )
        
        self.block3 = nn.Sequential(
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 2)
        )

    def forward(self, x):
        x = self.base(x)
        x = self.block1(x)
        y1, y2 = self.block2(x), self.block3(x)
        return y1, y2

model = Model().to(device)
model.load_state_dict(torch.load('ml/freshness/model.pth', map_location=torch.device('cpu')))
model.eval()

def image_transform(img, training=False):    
    if training:
        img = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.GaussianBlur(3, sigma=(0.1, 2.0)),
            transforms.RandomAdjustSharpness(3),
            transforms.Normalize(mean=[0, 0, 0], std=[1, 1, 1])
        ])(img)
    else:
        img = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((224, 224)),
            transforms.Normalize(mean=[0, 0, 0], std=[1, 1, 1])
        ])(img)
    return img

def predict_image(image_path):
    img = Image.open(image_path).convert('RGB')
    img = image_transform(img, training=False)
    img = img.unsqueeze(0).to(device)

    with torch.no_grad():
        output1, output2 = model(img)
        _, predicted_fruit = torch.max(output1, 1)
        _, predicted_fresh = torch.max(output2, 1)
    
    return predicted_fruit.item(), predicted_fresh.item()

@app.route('/freshness_test', methods=['POST'])
def freshness_test():
    try:
        image_file = request.files['image']
        image_path = "temp_image.jpg"
        image_file.save(image_path)
        
        # Perform freshness prediction
        fruit_label, freshness_label = predict_image(image_path)
        os.remove(image_path)

        return jsonify({'freshness_label': freshness_label})

    except Exception as e:
        return jsonify({'error': str(e)})



def chat_with_bot(user_query):
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",  # Choose a Groq-supported model
        messages=[{"role": "system", "content": "You are an AI agriculture assistant helping farmers with crop health, soil, and pest management."},
                  {"role": "user", "content": user_query}]
    )
    return response.choices[0].message.content

@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_query = request.form['user_query']
        bot_response = chat_with_bot(user_query)
        return jsonify({'response': bot_response})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    # This will create all tables
    app.run(host='0.0.0.0', port=10000, debug=True)

