import os
from app import app, db, User
from flask_bcrypt import generate_password_hash

# Delete the old database
db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
if os.path.exists(db_path):
    os.remove(db_path)
    print("Old database removed successfully.")

# Initialize the new database
with app.app_context():
    db.create_all()
    print("New database created successfully.")

    # Add sample data
    hashed_password = generate_password_hash("password123").decode('utf-8')
    user1 = User(
        username="John Doe",
        aadhar_no="123456789012",
        phone_no="9876543210",
        role="Farmer",
        email="john@example.com",
        password=hashed_password
    )
    user2 = User(
        username="Jane Smith",
        aadhar_no="098765432109",
        phone_no="8765432109",
        role="Consumer",
        email="jane@example.com",
        password=hashed_password
    )

    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    print("Sample data added successfully.")
