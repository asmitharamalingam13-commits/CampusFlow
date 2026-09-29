from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import db, login_manager
from app.models import User


# --------------------------------------------------
# AUTHENTICATION BLUEPRINT
# --------------------------------------------------

auth = Blueprint("auth", __name__)


# --------------------------------------------------
# LOAD LOGGED-IN USER
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        # Find user by email
        user = User.query.filter_by(
            email=email
        ).first()

        # Check email and password
        if user and user.check_password(password):

            # Check account status
            if not user.is_active:

                flash("Your account is inactive.")

                return redirect(
                    url_for("auth.login")
                )

            # Log the user in
            login_user(user)

            # Go to dashboard
            return redirect(
                url_for("main.dashboard")
            )

        # Invalid login
        flash("Invalid email or password.")

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@auth.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("auth.login")
    )