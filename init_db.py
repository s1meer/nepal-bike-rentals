from app import db, create_app
from app.models import Bike, User
from werkzeug.security import generate_password_hash

try:
    # Create the Flask app
    app = create_app()

    with app.app_context():
        # Check if bikes already exist to avoid duplicates
        if not Bike.query.first():
            # List of bikes to add
            bikes = [
                Bike(name="Pulsar 150", brand="Bajaj", daily_rate=1500.0, image_url="/static/images/pulsar150.jpg"),
                Bike(name="FZ 150 V2", brand="Yamaha", daily_rate=2000.0, image_url="/static/images/fz150v2.jpg"),
                Bike(name="Pulsar 220", brand="Bajaj", daily_rate=2000.0, image_url="/static/images/pulsar220.jpg"),
                Bike(name="Apache 200", brand="TVS", daily_rate=2250.0, image_url="/static/images/apache200.jpg"),
                Bike(name="NS200", brand="Bajaj", daily_rate=2250.0, image_url="/static/images/ns200.jpg"),
                Bike(name="FZ250", brand="Yamaha", daily_rate=2500.0, image_url="/static/images/fz250.jpg"),
                Bike(name="Xpulse 200", brand="Hero", daily_rate=2500.0, image_url="/static/images/xpulse200.jpg"),
                Bike(name="Royal Enfield Classic 350", brand="Royal Enfield", daily_rate=3250.0, image_url="/static/images/royalenfieldclassic350.jpg"),
            ]

            # Add bikes to the database
            for bike in bikes:
                db.session.add(bike)
            db.session.commit()
            print("Bikes added to the database.")
        else:
            print("Bikes already exist in the database, skipping bike initialization.")

        # Check if users already exist to avoid duplicates
        if not User.query.filter_by(email="test@example.com").first():
            # Add test user
            test_user = User(email="test@example.com", password=generate_password_hash("password123"))
            db.session.add(test_user)
            print("Test user added.")
        else:
            print("Test user already exists, skipping.")

        if not User.query.filter_by(email="admin@example.com").first():
            # Add admin user
            admin = User(email="admin@example.com", password=generate_password_hash("admin123"), is_admin=True)
            db.session.add(admin)
            print("Admin user added.")
        else:
            print("Admin user already exists, skipping.")

        # Commit any remaining changes
        db.session.commit()
        print("Database initialization completed successfully.")
except Exception as e:
    print(f"Error during database initialization: {str(e)}")