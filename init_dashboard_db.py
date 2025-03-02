from app import app, db, Crop, Order

# Initialize the dashboard database
with app.app_context():
    # Get the engine for the 'dashboard' bind
    engine = db.get_engine(app, bind='dashboard')
    # Create all tables for the 'dashboard' bind
    db.metadata.create_all(engine, tables=[Crop.__table__, Order.__table__])
    print("Dashboard database initialized successfully.")
