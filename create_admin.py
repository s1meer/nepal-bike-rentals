from app import app, db
from app.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check if admin user already exists
    existing_user = User.query.filter_by(email='sameer.ray.official@gmail.com').first()
    if existing_user:
        print(f"User {existing_user.email} already exists.")
    else:
        # Create new admin user
        new_admin = User(
            email='sameer.ray.official@gmail.com',
            password=generate_password_hash('your_secure_password'),  # Replace with your password
            is_admin=True
        )
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user {new_admin.email} created successfully!")