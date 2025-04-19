import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db').replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'sameer.ray.official@gmail.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_app_password')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'sameer.ray.official@gmail.com')
    app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
    app.config['ESEWA_MERCHANT_CODE'] = os.getenv('ESEWA_MERCHANT_CODE', 'EPAYTEST')
    app.config['ESEWA_SECRET_KEY'] = os.getenv('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
    app.config['ESEWA_API_URL'] = os.getenv('ESEWA_API_URL', 'https://rc-epay.esewa.com.np/api/epay/main/v2/form')
    app.config['ESEWA_STATUS_URL'] = os.getenv('ESEWA_STATUS_URL', 'https://rc-epay.esewa.com.np/api/epay/transaction/status/')
    app.config['MOCK_ESEWA'] = os.getenv('MOCK_ESEWA', 'True') == 'True'

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'

    # Import and register blueprints
    from app import routes, models, auth
    app.register_blueprint(routes.routes)
    app.register_blueprint(auth.auth)

    # Define user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    # Create database tables
    with app.app_context():
        db.create_all()

    return app