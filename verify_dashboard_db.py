from sqlalchemy import inspect
from app import app, db

with app.app_context():
    engine = db.get_engine(app, bind='dashboard')
    inspector = inspect(engine)
    print("Tables in dashboard.db:", inspector.get_table_names())
  