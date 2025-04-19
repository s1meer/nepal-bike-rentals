from app import db, create_app
from app.models import Bike, User, Booking, Notification
from werkzeug.security import generate_password_hash
from sqlalchemy.sql import text

try:
    # Create the Flask app
    app = create_app()
    print("DEBUG: Flask app created successfully in init_db.py.")

    with app.app_context():
        print("DEBUG: Entering app context in init_db.py.")
        # Drop all tables to ensure a clean slate
        print("DEBUG: Dropping all tables.")
        db.drop_all()
        print("DEBUG: All tables dropped.")

        # Create all tables
        print("DEBUG: Creating all tables.")
        db.create_all()
        print("DEBUG: db.create_all() called in init_db.py.")

        # Verify that the bike table exists by querying the SQLite database directly
        try:
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='bike';")).fetchone()
            if result:
                print("DEBUG: Bike table confirmed to exist in the database.")
            else:
                raise Exception("Bike table was not created by db.create_all().")
        except Exception as e:
            print(f"DEBUG: Failed to verify bike table existence. Error: {str(e)}")
            raise

        # Add bikes to the database
        bikes = [
            Bike(name="Pulsar 150", brand="Bajaj", daily_rate=1500.0, image_url="/static/images/pulsar150.jpg"),
            Bike(name="FZ 150 V2", brand="Yamaha", daily_rate=2000.0, image_url="/static/images/fz150v2.jpg"),
            Bike(name="Pulsar 220", brand="Bajaj", daily_rate=2000.0, image_url="/static/images/pulsar220.jpg"),
            Bike(name="Apache 200", brand="TVS", daily_rate=2250.0, image_url="/static/images/apache200.jpg"),
            Bike(name="NS200", brand="Bajaj", daily_rate=2250.0, image_url="/static/images/ns200.jpg"),
            Bike(name="FZ250", brand="Yamaha", daily_rate=2500.0, image_url="/static/images/fz250.jpg"),
            Bike(name="Xpulse 200", brand="Hero", daily_rate=2500.0, image_url="/static/images/xpulse_200.jpg"),
            Bike(name="Royal Enfield Classic 350", brand="Royal Enfield", daily_rate=3250.0, image_url="/static/images/royalenfieldclassic350.jpg"),
        ]

        # Add bikes to the database
        for bike in bikes:
            db.session.add(bike)
        db.session.commit()
        print("Bikes added to the database.")

        # Add test user
        test_user = User(email="test@example.com", password=generate_password_hash("password123"))
        db.session.add(test_user)
        print("Test user added.")

        # Add admin user
        admin = User(email="admin@example.com", password=generate_password_hash("admin123"), is_admin=True)
        db.session.add(admin)
        print("Admin user added.")

        # Commit any remaining changes
        db.session.commit()
        print("Database initialization completed successfully.")
except Exception as e:
    print(f"Error during database initialization: {str(e)}")