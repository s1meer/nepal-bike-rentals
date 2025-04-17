from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.models import Bike, Booking, User
from app import db, mail, app
from flask_mail import Message
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import requests
import uuid
import hmac
import hashlib
import base64

routes = Blueprint('routes', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_signature(total_amount, transaction_uuid, product_code, secret_key):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    return base64.b64encode(hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()).decode('utf-8')

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

@routes.route('/booking_details', methods=['POST'])
@login_required
def booking_details():
    bike_id = request.form['bike_id']
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    
    # Validate dates
    if end_date < start_date:
        flash('End date must be on or after start date.')
        return redirect(url_for('routes.index'))
    
    return render_template('booking_details.html', bike_id=bike_id, start_date=start_date, end_date=end_date)

@routes.route('/submit_booking_details/<int:bike_id>/<start_date>/<end_date>', methods=['POST'])
@login_required
def submit_booking_details(bike_id, start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    name = request.form['name']
    address = request.form['address']
    contact = request.form['contact']
    
    # Ensure uploads directory exists
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Handle file upload
    if 'document' not in request.files:
        flash('No file uploaded.')
        return redirect(url_for('routes.index'))
    file = request.files['document']
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('routes.index'))
    if file and allowed_file(file.filename) and file.content_length <= 5 * 1024 * 1024:
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
    else:
        flash('Invalid file. Upload a PDF less than 5MB.')
        return redirect(url_for('routes.index'))
    
    # Calculate price
    bike = Bike.query.get(bike_id)
    days = (end_date - start_date).days + 1
    total_price = days * bike.daily_rate
    
    # Check for conflicts
    conflicts = Booking.query.filter(
        Booking.bike_id == bike_id,
        Booking.status.in_(['Pending', 'Approved']),
        Booking.start_date <= end_date,
        Booking.end_date >= start_date
    ).all()
    
    if conflicts:
        flash(f'This bike is already booked during the selected dates. Please choose another bike or dates.')
        return redirect(url_for('routes.index'))
    
    # Create booking
    booking = Booking(
        user_id=current_user.id,
        bike_id=bike_id,
        start_date=start_date,
        end_date=end_date,
        name=name,
        address=address,
        contact=contact,
        document_path=file_path,
        total_price=total_price,
        transaction_uuid=str(uuid.uuid4())
    )
    db.session.add(booking)
    db.session.commit()
    
    # Send email notification
    msg = Message('Booking Submitted', recipients=[current_user.email])
    msg.body = f"""
    Dear {name},
    
    Your booking for {bike.name} from {start_date} (8:00 AM) to {end_date} (6:00 PM) has been submitted and is pending admin approval.
    Total Price: NPR {total_price}
    
    Regards,
    Nepal Bike Rentals
    """
    mail.send(msg)
    
    flash('Booking submitted! Awaiting admin approval. Check your email for confirmation.')
    return redirect(url_for('routes.dashboard'))

@routes.route('/initiate_payment/<int:booking_id>')
@login_required
def initiate_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id or booking.status != 'Approved' or booking.payment_status != 'Pending':
        flash('Invalid booking or payment already processed.')
        return redirect(url_for('routes.dashboard'))
    
    bike = Bike.query.get(booking.bike_id)
    total_amount = booking.total_price
    transaction_uuid = booking.transaction_uuid
    product_code = app.config['ESEWA_MERCHANT_CODE']
    secret_key = app.config['ESEWA_SECRET_KEY']
    success_url = url_for('routes.payment_success', booking_id=booking_id, _external=True)
    failure_url = url_for('routes.payment_failure', booking_id=booking_id, _external=True)
    
    signature = generate_signature(total_amount, transaction_uuid, product_code, secret_key)
    
    # Send email notification
    msg = Message('Payment Initiated', recipients=[current_user.email])
    msg.body = f"""
    Dear {booking.name},
    
    Your booking for {bike.name} has been approved. Please complete the payment of NPR {total_amount} via eSewa.
    You will be redirected to the eSewa payment page.
    
    Regards,
    Nepal Bike Rentals
    """
    mail.send(msg)
    
    return render_template('esewa_payment_form.html',
                          amount=total_amount,
                          transaction_uuid=transaction_uuid,
                          product_code=product_code,
                          success_url=success_url,
                          failure_url=failure_url,
                          signature=signature)

@routes.route('/payment_success/<int:booking_id>')
def payment_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('routes.dashboard'))
    
    # Verify payment with eSewa status API
    response = requests.get(
        f"{app.config['ESEWA_STATUS_URL']}?product_code={app.config['ESEWA_MERCHANT_CODE']}&total_amount={booking.total_price}&transaction_uuid={booking.transaction_uuid}"
    )
    if response.status_code == 200 and response.json().get('status') == 'COMPLETE':
        booking.payment_status = 'Completed'
        db.session.commit()
        
        # Send email notification
        msg = Message('Payment Successful', recipients=[current_user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your payment of NPR {booking.total_price} for {booking.bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) was successful.
        
        Regards,
        Nepal Bike Rentals
        """
        mail.send(msg)
        flash('Payment successful! Booking confirmed.')
    else:
        booking.payment_status = 'Failed'
        db.session.commit()
        
        # Send email notification
        msg = Message('Payment Failed', recipients=[current_user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your payment for {booking.bike.name} failed. Please try again or contact support at 9802829195, 9809655756, 9844066207.
        
        Regards,
        Nepal Bike Rentals
        """
        mail.send(msg)
        flash('Payment failed. Please try again.')
    
    return redirect(url_for('routes.dashboard'))

@routes.route('/payment_failure/<int:booking_id>')
def payment_failure(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('routes.dashboard'))
    
    booking.payment_status = 'Failed'
    db.session.commit()
    
    # Send email notification
    msg = Message('Payment Failed', recipients=[current_user.email])
    msg.body = f"""
    Dear {booking.name},
    
    Your payment for {booking.bike.name} failed. Please try again or contact support at 9802829195, 9809655756, 9844066207.
    
    Regards,
    Nepal Bike Rentals
    """
    mail.send(msg)
    flash('Payment failed. Please try again.')
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
    for booking in bookings:
        conflicts = Booking.query.filter(
            Booking.bike_id == booking.bike_id,
            Booking.id != booking.id,
            Booking.status.in_(['Pending', 'Approved']),
            Booking.start_date <= booking.end_date,
            Booking.end_date >= booking.start_date
        ).all()
        booking.conflicts = len(conflicts) > 0
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
    image_url = request.form['image_url']
    bike = Bike(name=name, brand=brand, daily_rate=daily_rate, image_url=image_url)
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
    user = User.query.get(booking.user_id)
    bike = Bike.query.get(booking.bike_id)
    
    if action == 'approve':
        booking.status = 'Approved'
        msg = Message('Booking Approved', recipients=[user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your booking for {bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) has been approved.
        Please complete the payment of NPR {booking.total_price} via eSewa.
        
        Regards,
        Nepal Bike Rentals
        """
    elif action == 'cancel':
        booking.status = 'Cancelled'
        msg = Message('Booking Cancelled', recipients=[user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Sorry, your booking for {bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) has been cancelled due to a scheduling conflict.
        Please choose another bike or dates.
        
        Regards,
        Nepal Bike Rentals
        """
    db.session.commit()
    mail.send(msg)
    flash(f'Booking {action}d')
    return redirect(url_for('routes.admin'))

@routes.route('/download_document/<int:booking_id>')
@login_required
def download_document(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    return send_file(booking.document_path, as_attachment=True)