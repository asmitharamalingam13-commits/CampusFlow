from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3


db = SQLAlchemy()

login_manager = LoginManager()


@event.listens_for(Engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):

    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = "campusflow-development-secret"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///campusflow.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager.init_app(app)

    login_manager.login_view = "auth.login"


    # Import models
    from app.models import User


    # Authentication
    from app.auth import auth
    app.register_blueprint(auth)


    # Main routes
    from app.routes import main
    app.register_blueprint(main)


    # Make has_permission available in Jinja templates
    from app.permissions import has_permission
    app.jinja_env.globals["has_permission"] = has_permission


    # Create database tables
    with app.app_context():
        db.create_all()


    return app