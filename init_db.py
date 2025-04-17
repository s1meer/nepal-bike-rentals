from app import app, db
from app.models import User, Bike
from werkzeug.security import generate_password_hash

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()
    
    # Add sample bikes
    bikes = [
        Bike(name="Royal Enfield Classic 350", brand="Royal Enfield", daily_rate=1200, weekly_rate=7800, monthly_rate=30000, image_url="https://via.placeholder.com/400x300?text=Royal+Enfield"),
        Bike(name="Pulsar 150", brand="Pulsar", daily_rate=500, weekly_rate=3250, monthly_rate=12500, image_url="https://via.placeholder.com/400x300?text=Pulsar+150"),
        Bike(name="Honda CB Shine", brand="Honda", daily_rate=600, weekly_rate=3900, monthly_rate=15000, image_url="https://via.placeholder.com/400x300?text=Honda+CB+Shine")
    ]
    db.session.bulk_save_objects(bikes)
    
    # Add admin user
    admin = User(email="admin@example.com", password=generate_password_hash("admin123"), is_admin=True)
    db.session.add(admin)
    db.session.commit()
    print("Database initialized with sample data.")
