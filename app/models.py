from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# ==================================================
# USER MODEL
# ==================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    student_profile = db.relationship(
    "Student",
    back_populates="user",
    uselist=False,
    foreign_keys="Student.user_id"
)
    

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email}>"


# ==================================================
# STUDENT MODEL
# ==================================================

class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Connect Student to User
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    # Mandatory 15-character alphanumeric RA Number
    ra_number = db.Column(
        db.String(15),
        unique=True,
        nullable=False
    )
    # Class Mentor responsible for OD approval
    class_mentor_id = db.Column(
    db.Integer,
    db.ForeignKey("users.id"),
    nullable=True
)
    class_mentor = db.relationship(
    "User",
    foreign_keys=[class_mentor_id]
)

    user = db.relationship(
    "User",
    back_populates="student_profile",
    uselist=False,
    foreign_keys=[user_id]
)

    # Database-level RA validation
    __table_args__ = (
        db.CheckConstraint(
            "length(ra_number) = 15",
            name="check_ra_length"
        ),

        db.CheckConstraint(
            "ra_number NOT GLOB '*[^A-Za-z0-9]*'",
            name="check_ra_alphanumeric"
        ),
    )

    def __repr__(self):
        return f"<Student {self.ra_number}>"


# ==================================================
# CLUB MODEL
# ==================================================

class Club(db.Model):
    __tablename__ = "clubs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    club_admin_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    faculty_coordinator_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    def __repr__(self):
        return f"<Club {self.name}>"


# ==================================================
# CLUB MEMBERSHIP MODEL
# ==================================================

class ClubMember(db.Model):
    __tablename__ = "club_members"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    club_id = db.Column(
        db.Integer,
        db.ForeignKey("clubs.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    joined_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    # Prevent duplicate club membership
    __table_args__ = (
        db.UniqueConstraint(
            "club_id",
            "student_id",
            name="unique_club_student"
        ),
    )

    def __repr__(self):
        return f"<ClubMember club={self.club_id} student={self.student_id}>"

# ==================================================
# DYNAMIC CLUB ROLE MODEL
# ==================================================

class ClubRole(db.Model):
    __tablename__ = "club_roles"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    club_id = db.Column(
        db.Integer,
        db.ForeignKey("clubs.id"),
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "club_id",
            "name",
            name="unique_club_role"
        ),
    )

    def __repr__(self):
        return f"<ClubRole club={self.club_id} name={self.name}>"
# ==================================================
# DYNAMIC CLUB ROLE PERMISSION MODEL
# ==================================================

class ClubRolePermission(db.Model):
    __tablename__ = "club_role_permissions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    club_role_id = db.Column(
        db.Integer,
        db.ForeignKey("club_roles.id"),
        nullable=False
    )

    permission = db.Column(
        db.String(100),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    # Same permission cannot be added twice to one role
    __table_args__ = (
        db.UniqueConstraint(
            "club_role_id",
            "permission",
            name="unique_role_permission"
        ),
    )

    def __repr__(self):
        return (
            f"<ClubRolePermission "
            f"role={self.club_role_id} "
            f"permission={self.permission}>"
        )
# ==================================================
# CLUB MEMBER ROLE ASSIGNMENT
# ==================================================

class ClubMemberRole(db.Model):
    __tablename__ = "club_member_roles"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    club_member_id = db.Column(
        db.Integer,
        db.ForeignKey("club_members.id"),
        nullable=False
    )

    club_role_id = db.Column(
        db.Integer,
        db.ForeignKey("club_roles.id"),
        nullable=False
    )

    assigned_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "club_member_id",
            "club_role_id",
            name="unique_member_role"
        ),
    )

    def __repr__(self):
        return (
            f"<ClubMemberRole "
            f"member={self.club_member_id} "
            f"role={self.club_role_id}>"
        )
# ==================================================
# EVENT MODEL
# ==================================================

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    club_id = db.Column(
        db.Integer,
        db.ForeignKey("clubs.id"),
        nullable=False
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    event_date = db.Column(
        db.Date,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    venue = db.Column(
        db.String(150),
        nullable=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(40),
        nullable=False,
        default="DRAFT"
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    rejection_reason = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    # Database validation
    __table_args__ = (
        db.CheckConstraint(
            "capacity > 0",
            name="check_event_capacity"
        ),

        db.CheckConstraint(
            "end_time > start_time",
            name="check_event_time"
        ),

        db.CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'PENDING_FACULTY_APPROVAL', "
            "'APPROVED', "
            "'REJECTED', "
            "'ONGOING', "
            "'COMPLETED', "
            "'CANCELLED'"
            ")",
            name="check_event_status"
        ),
    )

    def __repr__(self):
        return f"<Event {self.title}>"


# ==================================================
# EVENT REGISTRATION MODEL
# ==================================================

class EventRegistration(db.Model):
    __tablename__ = "event_registrations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    registered_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="REGISTERED"
    )

    # Prevent duplicate registration
    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "student_id",
            name="unique_event_student_registration"
        ),

        db.CheckConstraint(
            "status IN ('REGISTERED', 'CANCELLED')",
            name="check_registration_status"
        ),
    )

    def __repr__(self):
        return (
            f"<EventRegistration "
            f"event={self.event_id} "
            f"student={self.student_id}>"
        )


# ==================================================
# TIMETABLE STRUCTURE MODEL
# ==================================================

class TimetableStructure(db.Model):
    __tablename__ = "timetable_structures"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    scope = db.Column(
        db.String(100),
        nullable=False
    )

    effective_from = db.Column(
        db.Date,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )


# ==================================================
# TIMETABLE PERIOD MODEL
# ==================================================

class TimetablePeriod(db.Model):
    __tablename__ = "timetable_periods"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    timetable_id = db.Column(
        db.Integer,
        db.ForeignKey("timetable_structures.id"),
        nullable=False
    )

    period_order = db.Column(
        db.Integer,
        nullable=False
    )

    label = db.Column(
        db.String(50),
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    period_type = db.Column(
        db.String(20),
        nullable=False
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=False
    )

    # Database validation
    __table_args__ = (
        db.CheckConstraint(
            "end_time > start_time",
            name="check_period_time"
        ),

        db.CheckConstraint(
            "period_type IN ('CLASS', 'BREAK', 'LUNCH')",
            name="check_period_type"
        ),

        db.CheckConstraint(
            "duration_minutes > 0",
            name="check_period_duration"
        ),

        db.UniqueConstraint(
            "timetable_id",
            "period_order",
            name="unique_period_order"
        ),
    )

    def __repr__(self):
        return (
            f"<TimetablePeriod "
            f"{self.label} "
            f"{self.start_time}-{self.end_time}>"
        )
    # ==================================================
# OD REQUEST MODEL
# ==================================================

class ODRequest(db.Model):
    __tablename__ = "od_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Student applying for OD
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    # Event for which OD is requested
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    # Class Mentor who must approve/reject
    mentor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PENDING"
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    decision_reason = db.Column(
        db.Text,
        nullable=True
    )

    requested_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    decided_at = db.Column(
        db.DateTime,
        nullable=True
    )
    # Generated only when faculty marks the student PRESENT
    approval_code = db.Column(
        db.String(20),
        unique=True,
        nullable=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="check_od_status"
        ),

        db.UniqueConstraint(
            "student_id",
            "event_id",
            name="unique_student_event_od"
        ),
    )

    def __repr__(self):
        return (
            f"<ODRequest "
            f"student={self.student_id} "
            f"event={self.event_id} "
            f"status={self.status}>"
        )


# ==================================================
# OD PERIOD SNAPSHOT MODEL
# ==================================================

class ODPeriodSnapshot(db.Model):
    __tablename__ = "od_period_snapshots"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    od_request_id = db.Column(
        db.Integer,
        db.ForeignKey("od_requests.id"),
        nullable=False
    )

    # Original timetable period ID
    timetable_period_id = db.Column(
        db.Integer,
        db.ForeignKey("timetable_periods.id"),
        nullable=True
    )

    # Snapshot values
    period_order = db.Column(
        db.Integer,
        nullable=False
    )

    period_label = db.Column(
        db.String(50),
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        nullable=False
    )

    def __repr__(self):
        return (
            f"<ODPeriodSnapshot "
            f"OD={self.od_request_id} "
            f"Period={self.period_label}>"
        )
    

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PRESENT"
    )

    marked_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "student_id",
            name="uq_event_student_attendance"
        ),
    )
class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PRESENT"
    )

    marked_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "student_id",
            name="uq_event_student_attendance"
        ),
    )


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    certificate_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    issued_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    file_path = db.Column(
        db.String(500),
        nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "student_id",
            name="uq_event_student_certificate"
        ),
    )
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=True
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )
