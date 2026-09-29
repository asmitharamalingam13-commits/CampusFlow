from app import create_app, db
from app.models import User


# Create Flask application
app = create_app()


# ==================================================
# TEST ACCOUNTS
# ==================================================

test_users = [
    {
        "name": "Super Admin",
        "email": "superadmin@campusflow.com",
        "password": "SuperAdmin@123",
        "role": "SUPER_ADMIN"
    },
    {
        "name": "System Admin",
        "email": "admin@campusflow.com",
        "password": "Admin@123",
        "role": "ADMIN"
    },
    {
        "name": "Faculty Member",
        "email": "faculty@campusflow.com",
        "password": "Faculty@123",
        "role": "FACULTY"
    },
    {
        "name": "Club Administrator",
        "email": "clubadmin@campusflow.com",
        "password": "ClubAdmin@123",
        "role": "CLUB_ADMIN"
    },
    {
        "name": "Student Member",
        "email": "student@campusflow.com",
        "password": "Student@123",
        "role": "STUDENT"
    },
    {
        "name": "Student Member 2",
        "email": "student2@campusflow.com",
        "password": "Student2@123",
        "role": "STUDENT"
    }
]


# ==================================================
# WORK INSIDE FLASK APPLICATION
# ==================================================

with app.app_context():

    for data in test_users:

        # Check whether the user already exists
        existing_user = User.query.filter_by(
            email=data["email"]
        ).first()

        if existing_user:
            print(f"Already exists: {data['email']}")
            continue

        # Create new user
        user = User(
            name=data["name"],
            email=data["email"],
            role=data["role"]
        )

        # Hash the password securely
        user.set_password(data["password"])

        # Add user to database
        db.session.add(user)

        print(f"Created: {data['email']}")

    # Save all changes
    db.session.commit()

    print()
    print("==========================================")
    print("CampusFlow seed completed!")
    print("==========================================")
    print()
    print("Test Accounts:")
    print("------------------------------------------")
    print("Super Admin : superadmin@campusflow.com")
    print("System Admin: admin@campusflow.com")
    print("Faculty     : faculty@campusflow.com")
    print("Club Admin  : clubadmin@campusflow.com")
    print("Student 1   : student@campusflow.com")
    print("Student 2   : student2@campusflow.com")
    print("------------------------------------------")