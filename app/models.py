from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Bike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    weekly_rate = db.Column(db.Float, nullable=False)
    monthly_rate = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')
