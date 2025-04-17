from app import app, db
from app.models import User, Bike
from werkzeug.security import generate_password_hash

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()
    
    # Add sample bikes
    bikes = [
        Bike(name="Pulsar 150", brand="Pulsar", daily_rate=1500, image_url="/static/images/pulsar150.jpg"),
        Bike(name="FZ 150 V2", brand="Yamaha", daily_rate=2000, image_url="/static/images/fz150v2.jpg"),
        Bike(name="Pulsar 220", brand="Pulsar", daily_rate=2000, image_url="/static/images/pulsar220.jpg"),
        Bike(name="Apache 200", brand="Apache", daily_rate=2250, image_url="/static/images/apache200.jpg"),
        Bike(name="NS200", brand="Pulsar", daily_rate=2250, image_url="/static/images/ns200.jpg"),
        Bike(name="FZ250", brand="Yamaha", daily_rate=2500, image_url="/static/images/fz250.jpg"),
        Bike(name="Xpulse 200", brand="Hero", daily_rate=2500, image_url="/static/images/xpulse200.jpg"),
        Bike(name="Royal Enfield Classic 350", brand="Royal Enfield", daily_rate=3250, image_url="/static/images/royalenfieldclassic350.jpg")
    ]
    db.session.bulk_save_objects(bikes)
    
    # Add test user
    test_user = User(email="test@example.com", password=generate_password_hash("password123"))
    db.session.add(test_user)
    
    # Add admin user
    admin = User(email="admin@example.com", password=generate_password_hash("admin123"), is_admin=True)
    db.session.add(admin)
    db.session.commit()
    print("Database initialized with sample data.")