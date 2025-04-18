from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from app.models import Bike, Booking, User, Notification
from app import db, mail
from flask_mail import Message
from datetime import datetime
import os
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import requests
import uuid
import hmac
import hashlib
import base64
import urllib.parse

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
    print(f"DEBUG: Received bike_id = {bike_id}")  # Debug log
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    
    if end_date < start_date:
        flash('End date must be on or after start date.')
        return redirect(url_for('routes.index'))
    
    bike = Bike.query.get(bike_id)
    if not bike:
        flash('Bike not found.')
        print(f"DEBUG: Bike with ID {bike_id} not found in database.")  # Debug log
        return redirect(url_for('routes.index'))
    
    # Calculate total price server-side
    days = (end_date - start_date).days + 1  # Inclusive of start and end dates
    total_price = days * bike.daily_rate
    
    # Update the bike object with the selected dates and total price for rendering
    bikes = Bike.query.all()
    bike_dict = {bike.id: bike for bike in bikes}
    bike_dict[int(bike_id)].selected_start_date = start_date
    bike_dict[int(bike_id)].selected_end_date = end_date
    bike_dict[int(bike_id)].selected_days = days
    bike_dict[int(bike_id)].selected_total_price = total_price
    
    return render_template('index.html', bikes=bikes)

@routes.route('/submit_booking_details/<int:bike_id>/<start_date>/<end_date>', methods=['POST'])
@login_required
def submit_booking_details(bike_id, start_date, end_date):
    print(f"DEBUG: Submitting booking for bike_id = {bike_id}")  # Debug log
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    name = request.form['name']
    address = request.form['address']
    contact = request.form['contact']
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
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
        relative_path = os.path.join('static', 'Uploads', filename).replace('\\', '/')
    else:
        flash('Invalid file. Upload a PDF less than 5MB.')
        return redirect(url_for('routes.index'))
    
    bike = Bike.query.get(bike_id)
    if not bike:
        flash('Bike not found.')
        print(f"DEBUG: Bike with ID {bike_id} not found in database during submit.")  # Debug log
        return redirect(url_for('routes.index'))
    days = (end_date - start_date).days + 1
    total_price = days * bike.daily_rate
    
    conflicts = Booking.query.filter(
        Booking.bike_id == bike_id,
        Booking.status.in_(['Pending', 'Approved']),
        Booking.start_date <= end_date,
        Booking.end_date >= start_date
    ).all()
    
    if conflicts:
        flash('This bike is already booked during the selected dates. Please choose another bike or dates.')
        return redirect(url_for('routes.index'))
    
    booking = Booking(
        user_id=current_user.id,
        bike_id=bike_id,
        start_date=start_date,
        end_date=end_date,
        name=name,
        address=address,
        contact=contact,
        document_path=relative_path,
        total_price=total_price,
        transaction_uuid=str(uuid.uuid4())
    )
    db.session.add(booking)
    db.session.commit()
    
    try:
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
    except Exception as e:
        flash(f'Booking submitted, but email notification failed: {str(e)}')
    
    return redirect(url_for('routes.dashboard'))

@routes.route('/initiate_payment/<int:booking_id>')
@login_required
def initiate_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id or booking.status != 'Approved' or booking.payment_status != 'Pending':
        flash('Invalid booking or payment already processed.')
        return redirect(url_for('routes.dashboard'))
    
    bike = Bike.query.get(booking.bike_id)
    if not bike:
        flash('Bike not found.')
        return redirect(url_for('routes.dashboard'))
    total_amount = booking.total_price
    transaction_uuid = booking.transaction_uuid
    product_code = current_app.config['ESEWA_MERCHANT_CODE']
    secret_key = current_app.config['ESEWA_SECRET_KEY']
    success_url = url_for('routes.payment_success', booking_id=booking_id, _external=True)
    failure_url = url_for('routes.payment_failure', booking_id=booking_id, _external=True)
    
    # Mock payment for testing (bypass eSewa sandbox)
    if current_app.config.get('MOCK_ESEWA', False):
        flash('eSewa service is currently unavailable. Using mock payment for testing.')
        try:
            msg = Message('Payment Initiated (Mock)', recipients=[current_user.email])
            msg.body = f"""
            Dear {booking.name},
            
            Your booking for {bike.name} has been approved. In production, you would complete the payment of NPR {total_amount} via eSewa.
            Since eSewa is unavailable, a mock payment is being processed for testing.
            
            Regards,
            Nepal Bike Rentals
            """
            mail.send(msg)
        except Exception as e:
            flash(f'Mock payment initiation started, but email notification failed: {str(e)}')
        return redirect(url_for('routes.payment_success', booking_id=booking_id))
    
    try:
        signature = generate_signature(total_amount, transaction_uuid, product_code, secret_key)
    except Exception as e:
        flash(f'Failed to generate payment signature: {str(e)}')
        return redirect(url_for('routes.dashboard'))
    
    # Check eSewa API availability
    try:
        response = requests.head(current_app.config['ESEWA_API_URL'], timeout=5)
        if response.status_code not in (200, 301, 302):
            flash(f'eSewa service is unavailable (status {response.status_code}). Please try again later.')
            return redirect(url_for('routes.dashboard'))
    except requests.RequestException as e:
        flash(f'Unable to connect to eSewa service: {str(e)}. Please try again later.')
        return redirect(url_for('routes.dashboard'))
    
    # Generate eSewa QR code URL
    payment_data = {
        'amount': str(total_amount),
        'transaction_uuid': transaction_uuid,
        'product_code': product_code,
        'signature': signature,
        'success_url': success_url,
        'failure_url': failure_url
    }
    qr_code_url = f"{current_app.config['ESEWA_API_URL']}?{urllib.parse.urlencode(payment_data)}"
    
    try:
        msg = Message('Payment Initiated', recipients=[current_user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your booking for {bike.name} has been approved. Please complete the payment of NPR {total_amount} via eSewa.
        You will be redirected to the eSewa payment page.
        
        Regards,
        Nepal Bike Rentals
        """
        mail.send(msg)
    except Exception as e:
        flash(f'Payment initiation started, but email notification failed: {str(e)}')
    
    return render_template('esewa_payment_form.html',
                          amount=total_amount,
                          transaction_uuid=transaction_uuid,
                          product_code=product_code,
                          success_url=success_url,
                          failure_url=failure_url,
                          signature=signature,
                          esewa_api_url=current_app.config['ESEWA_API_URL'],
                          qr_code_url=qr_code_url,
                          bike_name=bike.name,
                          start_date=booking.start_date,
                          end_date=booking.end_date)

@routes.route('/payment_success/<int:booking_id>')
def payment_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('routes.dashboard'))
    
    # Mock payment bypass for testing
    if current_app.config.get('MOCK_ESEWA', False):
        booking.payment_status = 'Completed'
        db.session.commit()
        flash('Mock payment successful! Booking confirmed.')
        try:
            msg = Message('Mock Payment Successful', recipients=[current_user.email])
            msg.body = f"""
            Dear {booking.name},
            
            Your mock payment of NPR {booking.total_price} for {booking.bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) was successful.
            In production, this would be processed via eSewa.
            
            Regards,
            Nepal Bike Rentals
            """
            mail.send(msg)
        except Exception as e:
            flash(f'Mock payment successful, but email notification failed: {str(e)}')
        # Add a notification for the user
        notification = Notification(
            user_id=booking.user_id,
            message=f"Mock payment for {booking.bike.name} from {booking.start_date} to {booking.end_date} was successful."
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for('routes.dashboard'))
    
    try:
        response = requests.get(
            f"{current_app.config['ESEWA_STATUS_URL']}?product_code={current_app.config['ESEWA_MERCHANT_CODE']}&total_amount={booking.total_price}&transaction_uuid={booking.transaction_uuid}"
        )
        if response.status_code == 200 and response.json().get('status') == 'COMPLETE':
            booking.payment_status = 'Completed'
            db.session.commit()
            
            try:
                msg = Message('Payment Successful', recipients=[current_user.email])
                msg.body = f"""
                Dear {booking.name},
                
                Your payment of NPR {booking.total_price} for {booking.bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) was successful.
                
                Regards,
                Nepal Bike Rentals
                """
                mail.send(msg)
                flash('Payment successful! Booking confirmed.')
            except Exception as e:
                flash(f'Payment successful, but email notification failed: {str(e)}')
        else:
            booking.payment_status = 'Failed'
            db.session.commit()
            
            try:
                msg = Message('Payment Failed', recipients=[current_user.email])
                msg.body = f"""
                Dear {booking.name},
                
                Your payment for {booking.bike.name} failed. Please try again or contact support at 9802829195, 9809655756, 9844066207.
                
                Regards,
                Nepal Bike Rentals
                """
                mail.send(msg)
                flash('Payment failed. Please try again.')
            except Exception as e:
                flash(f'Payment failed, and email notification failed: {str(e)}')
    except Exception as e:
        flash(f'Payment verification failed: {str(e)}')
    
    return redirect(url_for('routes.dashboard'))

@routes.route('/payment_failure/<int:booking_id>')
def payment_failure(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('routes.dashboard'))
    
    booking.payment_status = 'Failed'
    db.session.commit()
    
    try:
        msg = Message('Payment Failed', recipients=[current_user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your payment for {booking.bike.name} failed. Please try again or contact support at 9802829195, 9809655756, 9844066207.
        
        Regards,
        Nepal Bike Rentals
        """
        mail.send(msg)
        flash('Payment failed. Please try again.')
    except Exception as e:
        flash(f'Payment failed, and email notification failed: {str(e)}')
    
    return redirect(url_for('routes.dashboard'))

@routes.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    
    # Check eSewa API availability for user notice
    esewa_unavailable = False
    if not current_app.config.get('MOCK_ESEWA', False):
        try:
            response = requests.head(current_app.config['ESEWA_API_URL'], timeout=5)
            if response.status_code not in (200, 301, 302):
                esewa_unavailable = True
        except requests.RequestException:
            esewa_unavailable = True
    
    return render_template('dashboard.html', bookings=bookings, notifications=notifications, esewa_unavailable=esewa_unavailable)

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
    
    # Calculate booking counts
    total_bookings = Booking.query.count()
    unique_users = db.session.query(Booking.user_id).distinct().count()
    
    users = User.query.all()
    bikes = Bike.query.all()
    return render_template('admin.html', bookings=bookings, users=users, bikes=bikes, total_bookings=total_bookings, unique_users=unique_users)

@routes.route('/admin/add_bike', methods=['POST'])
@login_required
def add_bike():
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    name = request.form['name']
    brand = request.form['brand']
    try:
        daily_rate = float(request.form['daily_rate'])
    except ValueError:
        flash('Invalid daily rate.')
        return redirect(url_for('routes.admin'))
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
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    booking = Booking.query.get(id)
    if not booking:
        flash('Booking not found.')
        return redirect(url_for('routes.admin'))
    user = User.query.get(booking.user_id)
    bike = Bike.query.get(booking.bike_id)
    if not user or not bike:
        flash('Invalid user or bike associated with booking.')
        return redirect(url_for('routes.admin'))
    
    if action == 'approve':
        if booking.status.lower() != 'pending':
            flash('Booking is not pending.')
            return redirect(url_for('routes.admin'))
        booking.status = 'Approved'
        notification_message = f"Your booking for {bike.name} from {booking.start_date} to {booking.end_date} has been approved."
        email_subject = 'Booking Approved'
        email_body = f"""
        Dear {booking.name},
        
        Your booking for {bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) has been approved.
        Please complete the payment of NPR {booking.total_price} via eSewa.
        
        Regards,
        Nepal Bike Rentals
        """
    elif action == 'cancel':
        if booking.status.lower() != 'pending':
            flash('Booking is not pending.')
            return redirect(url_for('routes.admin'))
        booking.status = 'Cancelled'
        notification_message = f"Your booking for {bike.name} from {booking.start_date} to {booking.end_date} has been cancelled."
        email_subject = 'Booking Cancelled'
        email_body = f"""
        Dear {booking.name},
        
        Sorry, your booking for {bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) has been cancelled due to a scheduling conflict.
        Please choose another bike or dates.
        
        Regards,
        Nepal Bike Rentals
        """
    else:
        flash('Invalid action.')
        return redirect(url_for('routes.admin'))
    
    notification = Notification(
        user_id=user.id,
        message=notification_message
    )
    db.session.add(notification)
    db.session.commit()
    
    try:
        msg = Message(email_subject, recipients=[user.email])
        msg.body = email_body
        mail.send(msg)
        flash(f'Booking {action}d successfully.')
    except Exception as e:
        flash(f'Booking {action}d, but email notification failed: {str(e)}')
    
    return redirect(url_for('routes.admin'))

@routes.route('/admin/resend_payment_qr/<int:booking_id>')
@login_required
def resend_payment_qr(booking_id):
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'Approved' or booking.payment_status != 'Pending':
        flash('Booking is not approved or payment is not pending.')
        return redirect(url_for('routes.admin'))
    
    user = User.query.get(booking.user_id)
    bike = Bike.query.get(booking.bike_id)
    if not user or not bike:
        flash('Invalid user or bike associated with booking.')
        return redirect(url_for('routes.admin'))
    
    total_amount = booking.total_price
    transaction_uuid = booking.transaction_uuid
    product_code = current_app.config['ESEWA_MERCHANT_CODE']
    secret_key = current_app.config['ESEWA_SECRET_KEY']
    success_url = url_for('routes.payment_success', booking_id=booking.id, _external=True)
    failure_url = url_for('routes.payment_failure', booking_id=booking.id, _external=True)
    
    try:
        signature = generate_signature(total_amount, transaction_uuid, product_code, secret_key)
    except Exception as e:
        flash(f'Failed to generate payment signature: {str(e)}')
        return redirect(url_for('routes.admin'))
    
    # Generate eSewa QR code URL
    payment_data = {
        'amount': str(total_amount),
        'transaction_uuid': transaction_uuid,
        'product_code': product_code,
        'signature': signature,
        'success_url': success_url,
        'failure_url': failure_url
    }
    qr_code_url = f"{current_app.config['ESEWA_API_URL']}?{urllib.parse.urlencode(payment_data)}"
    
    # Send email with QR code URL
    try:
        msg = Message('eSewa Payment QR Code', recipients=[user.email])
        msg.body = f"""
        Dear {booking.name},
        
        Your booking for {bike.name} from {booking.start_date} (8:00 AM) to {booking.end_date} (6:00 PM) requires payment of NPR {total_amount}.
        Since direct payment failed, please scan the QR code at the following link to complete your payment via eSewa:
        
        QR Code URL: {qr_code_url}
        
        Alternatively, you can try paying again by logging into your dashboard.
        
        Regards,
        Nepal Bike Rentals
        """
        mail.send(msg)
        flash('Payment QR code sent to user’s email successfully.')
    except Exception as e:
        flash(f'Failed to send payment QR code email: {str(e)}')
    
    return redirect(url_for('routes.admin'))

@routes.route('/download_document/<int:booking_id>')
@login_required
def download_document(booking_id):
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('routes.index'))
    booking = Booking.query.get_or_404(booking_id)
    absolute_path = os.path.join(current_app.root_path, booking.document_path)
    if not os.path.exists(absolute_path):
        flash('Document not found.')
        return redirect(url_for('routes.admin'))
    return send_file(absolute_path, mimetype='application/pdf', as_attachment=False)

@routes.route('/init-db', methods=['GET'])
def init_db():
    if not Bike.query.first():
        bikes = [
            Bike(name="Pulsar 150", brand="Bajaj", daily_rate=1500.0, image_url="/static/images/pulsar_150.jpg"),
            Bike(name="FZ 150 V2", brand="Yamaha", daily_rate=2000.0, image_url="/static/images/fz_150_v2.jpg"),
            Bike(name="Pulsar 220", brand="Bajaj", daily_rate=2000.0, image_url="/static/images/pulsar_220.jpg"),
            Bike(name="Apache 200", brand="TVS", daily_rate=2250.0, image_url="/static/images/apache_200.jpg"),
            Bike(name="NS200", brand="Bajaj", daily_rate=2250.0, image_url="/static/images/ns200.jpg"),
            Bike(name="FZ250", brand="Yamaha", daily_rate=2500.0, image_url="/static/images/fz250.jpg"),
            Bike(name="Xpulse 200", brand="Hero", daily_rate=2500.0, image_url="/static/images/xpulse_200.jpg"),
            Bike(name="Royal Enfield Classic 350", brand="Royal Enfield", daily_rate=3250.0, image_url="/static/images/royal_enfield_classic_350.jpg"),
        ]
        for bike in bikes:
            db.session.add(bike)
        db.session.commit()
        print("Bikes added to the database.")
    else:
        print("Bikes already exist in the database, skipping bike initialization.")

    if not User.query.filter_by(email="test@example.com").first():
        test_user = User(email="test@example.com", password=generate_password_hash("password123"))
        db.session.add(test_user)
        print("Test user added.")
    else:
        print("Test user already exists, skipping.")

    if not User.query.filter_by(email="admin@example.com").first():
        admin = User(email="admin@example.com", password=generate_password_hash("admin123"), is_admin=True)
        db.session.add(admin)
        print("Admin user added.")
    else:
        print("Admin user already exists, skipping.")

    db.session.commit()
    return "Database initialized with sample data."