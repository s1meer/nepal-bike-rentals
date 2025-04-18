from app import app, db
from app.models import Booking
import os

with app.app_context():
    bookings = Booking.query.all()
    for booking in bookings:
        if booking.document_path:
            # Extract filename from absolute or incorrect path
            filename = os.path.basename(booking.document_path)
            # Set correct relative path
            correct_path = os.path.join('static', 'uploads', filename).replace('\\', '/')
            booking.document_path = correct_path
            print(f"Updated path for booking {booking.id}: {booking.document_path}")
    db.session.commit()
    print("All booking paths updated.")