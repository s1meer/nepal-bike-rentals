from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Bike, Booking, User
from app import db
import razorpay
from twilio.rest import Client
import os

routes = Blueprint('routes', __name__)

# Razorpay and Twilio setup
razorpay_client = razorpay.Client(auth=("your_key_id", "your_key_secret"))
twilio_client = Client("your_account_sid", "your_auth_token")

@routes.route('/')
def index():
    bikes = Bike.query.all()
    return render_template('index.html', bikes=bikes)

@routes.route('/filter_bikes', methods=['POST'])
def filter_bikes():
    brand = request.form['brand']
    if brand == 'all':
        bikes = Bike.query.all()
    else:
        bikes = Bike.query.filter_by(brand=brand).all()
    return render_template('index.html', bikes=bikes)

@routes.route('/book', methods=['POST'])
@login_required
def book():
    bike_id = request.form['bike_id']
    date = request.form['date']
    duration = request.form['duration']
    booking = Booking(user_id=current_user.id, bike_id=bike_id, date=date, duration=duration)
    db.session.add(booking)
    db.session.commit()

    # Razorpay payment
    amount = 50000  # NPR 500 in paisa
    order = razorpay_client.order.create({'amount': amount, 'currency': 'INR', 'payment_capture': '1'})
    
    # Twilio SMS
    twilio_client.messages.create(
        body=f'Booking confirmed for {date}. Order ID: {order["id"]}',
        from_='your_twilio_number',
        to='user_phone_number'
    )
    
    flash('Booking successful! Payment processed.')
    return redirect(url_for('routes.dashboard'))

@routes.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', bookings=bookings)

@routes.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    bookings = Booking.query.all()
    users = User.query.all()
    bikes = Bike.query.all()
    return render_template('admin.html', bookings=bookings, users=users, bikes=bikes)

@routes.route('/admin/add_bike', methods=['POST'])
@login_required
def add_bike():
    if not current_user.is_admin:
        return redirect(url_for('routes.index'))
    name = request.form['name']
    brand = request.form['brand']
    daily_rate = float(request.form['daily_rate'])
    weekly_rate = float(request.form['weekly_rate'])
    monthly_rate = float(request.form['monthly_rate'])
    image_url = request.form['image_url']
    bike = Bike(name=name, brand=brand, daily_rate=daily_rate, weekly_rate=weekly_rate, monthly_rate=monthly_rate, image_url=image_url)
    db.session.add(bike)
    db.session.commit()
    flash('Bike added successfully')
    return redirect(url_for('routes.admin'))

@routes.route('/admin/update_booking/<int:id>/<action>')
@login_required
def update_booking(id, action):
    if not current_user.is_admin:
        return redirect(url_for('routes.index'))
    booking = Booking.query.get(id)
    if action == 'approve':
        booking.status = 'Approved'
    elif action == 'cancel':
        booking.status = 'Cancelled'
    db.session.commit()
    flash(f'Booking {action}d')
    return redirect(url_for('routes.admin'))
