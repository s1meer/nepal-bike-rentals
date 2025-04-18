from app import app, db
from app.models import Booking, User, Bike
from datetime import datetime

with app.app_context():
    bookings = Booking.query.all()
    if not bookings:
        print("No bookings found in the database.")
    else:
        print("Bookings in database:")
        for booking in bookings:
            user = User.query.get(booking.user_id)
            bike = Bike.query.get(booking.bike_id)
            print(f"ID: {booking.id}")
            print(f"User: {user.email if user else 'Unknown'}")
            print(f"Bike: {bike.name if bike else 'Unknown'}")
            print(f"Start Date: {booking.start_date}")
            print(f"End Date: {booking.end_date}")
            print(f"Price (NPR): {booking.total_price}")
            print(f"Name: {booking.name}")
            print(f"Address: {booking.address}")
            print(f"Contact: {booking.contact}")
            print(f"Document Path: {booking.document_path}")
            print(f"Status: {booking.status}")
            print(f"Payment Status: {booking.payment_status}")
            print(f"Transaction UUID: {booking.transaction_uuid}")
            print("-" * 50)