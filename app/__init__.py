from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'LPwsxbq2WQ5hquyUSibnlp68LSM0KPnT'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sameer.ray.official@gmail.com'
app.config['MAIL_PASSWORD'] = 'qrstuvwxyzabcdefg'  # New App Password
app.config['MAIL_DEFAULT_SENDER'] = 'sameer.ray.official@gmail.com'
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
app.config['ESEWA_MERCHANT_CODE'] = 'EPAYTEST'
app.config['ESEWA_SECRET_KEY'] = '8gBm/:&EnhH.1/q'
app.config['ESEWA_API_URL'] = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
app.config['ESEWA_STATUS_URL'] = 'https://rc-epay.esewa.com.np/api/epay/transaction/status/'
app.config['MAIL_PASSWORD'] = 'your-sendgrid-api-key'
app.config['MAIL_USERNAME'] = 'apikey'
app.config['ESEWA_MERCHANT_CODE'] = os.getenv('ESEWA_MERCHANT_CODE', 'EPAYTEST')
#app.config['ESEWA_SECRET_KEY'] = os.getenv('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
#app.config['ESEWA_API_URL'] = os.getenv('ESEWA_API_URL', 'https://rc-epay.esewa.com.np/api/epay/main/v2/form')
#app.config['ESEWA_STATUS_URL'] = os.getenv('ESEWA_STATUS_URL', 'https://rc-epay.esewa.com.np/api/epay/transaction/status/')
app.config['MOCK_ESEWA'] = os.getenv('MOCK_ESEWA', 'True') == 'True'


# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
mail = Mail(app)
login_manager.login_view = 'auth.login'

# Import routes, models, and auth after app and db initialization
from app import routes, models, auth

# Register Blueprints
app.register_blueprint(routes.routes)
app.register_blueprint(auth.auth)

# Define user_loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()