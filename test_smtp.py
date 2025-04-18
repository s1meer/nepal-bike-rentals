import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Test email from Flask-Mail")
msg['Subject'] = 'Test Email'
msg['From'] = 'sameer.ray.official@gmail.com'  # Your Gmail email
msg['To'] = 'sy288136@gmail.com'        # Test recipient email

try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('sameer.ray.official@gmail.com', 'lyjr jedt nsfd hzyq ')  # Your App Password
        server.send_message(msg)
    print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")