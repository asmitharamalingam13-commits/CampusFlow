from functools import wraps
from flask import abort
from flask_login import current_user
from app import db
from app.models import ODPeriodSnapshot, Event
# ==================================================
# CAMPUSFLOW ROLE PERMISSIONS
# ==================================================

ROLE_PERMISSIONS = {

    "SUPER_ADMIN": {
        "manage_users",
        "manage_roles",
        "manage_timetable",
        "manage_clubs",
        "view_analytics",
        "view_audit_logs",
    },

    "ADMIN": {
        "manage_users",
        "manage_clubs",
        "view_analytics",
    },

    "FACULTY": {
        "approve_events",
        "approve_od",
        "view_analytics",
        "send_messages",
    },

    "CLUB_ADMIN": {
        "manage_club",
        "create_event",
        "manage_event",
        "manage_attendance",
        "issue_badges",
        "view_club_analytics",
        "send_messages",
    },

    "STUDENT": {
        "view_events",
        "register_event",
        "apply_od",
        "view_certificates",
        "view_badges",
        "send_messages",
    }
}

# ==================================================
# DYNAMIC CLUB PERMISSIONS
# ==================================================

DYNAMIC_CLUB_PERMISSIONS = {

    "create_event":
        "Create new club events",

    "manage_event":
        "Edit event details",

    "manage_venue":
        "Manage event venue",

    "manage_capacity":
        "Manage event capacity",

    "submit_event":
        "Submit event for Faculty approval",

    "view_registrations":
        "View student registrations",

    "manage_registrations":
        "Manage event registrations",

    "manage_attendance":
        "Manage event attendance",

    "issue_certificates":
        "Generate and issue certificates",

    "manage_badges":
        "Create and award badges",

    "view_od":
        "View On-Duty requests",

    "send_messages":
        "Send club communication",

    "view_analytics":
        "View club analytics",
}
# ==================================================
# CHECK PERMISSION
# ==================================================

# ==================================================
# CHECK SYSTEM + DYNAMIC CLUB ROLE PERMISSION
# ==================================================

def has_permission(permission, club_id=None):

    if not current_user.is_authenticated:
        return False

    # ----------------------------------------------
    # 1. Check fixed system role permissions
    # ----------------------------------------------

    user_permissions = ROLE_PERMISSIONS.get(
        current_user.role,
        set()
    )

    if permission in user_permissions:
        return True

    # ----------------------------------------------
    # 2. Check dynamic club role permissions
    # ----------------------------------------------

    if not club_id:
        return False

    from app.models import (
        Student,
        ClubMember,
        ClubMemberRole,
        ClubRolePermission
    )

    # Find student profile
    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return False

    # Find membership in this club
    member = ClubMember.query.filter_by(
        club_id=club_id,
        student_id=student.id
    ).first()

    if not member:
        return False

    # Find roles assigned to this member
    assignments = ClubMemberRole.query.filter_by(
        club_member_id=member.id
    ).all()

    # Check every assigned role
    for assignment in assignments:

        role_permission = ClubRolePermission.query.filter_by(
            club_role_id=assignment.club_role_id,
            permission=permission
        ).first()

        if role_permission:
            return True

    return False
# ==================================================
# BACKEND PERMISSION DECORATOR
# ==================================================

def permission_required(permission, club_id=None):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                abort(401)

            # Get club_id from route if not passed directly
            actual_club_id = club_id

            if actual_club_id is None:
                actual_club_id = kwargs.get("club_id")

            if not has_permission(
                permission,
                actual_club_id
            ):
                abort(403)

            return function(*args, **kwargs)

        return wrapper

    return decorator


# ==================================================
# BACKEND ROLE DECORATOR
# ==================================================

def role_required(*allowed_roles):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                abort(401)

            if current_user.role not in allowed_roles:
                abort(403)

            return function(*args, **kwargs)

        return wrapper

    return decorator
# ==================================================
# EVENT STATUS TRANSITIONS
# ==================================================

EVENT_STATUS_TRANSITIONS = {

    "DRAFT": {
        "PENDING_FACULTY_APPROVAL"
    },

    "PENDING_FACULTY_APPROVAL": {
        "APPROVED",
        "REJECTED"
    },

    "APPROVED": {
        "ONGOING",
        "CANCELLED"
    },

    "ONGOING": {
        "COMPLETED",
        "CANCELLED"
    },

    "COMPLETED": set(),

    "CANCELLED": set(),

    "REJECTED": {
        "PENDING_FACULTY_APPROVAL"
    }
}


def can_change_event_status(current_status, new_status):

    allowed_statuses = EVENT_STATUS_TRANSITIONS.get(
        current_status,
        set()
    )

    return new_status in allowed_statuses
# ==================================================
# EVENT STATUS TRANSITIONS
# ==================================================

EVENT_STATUS_TRANSITIONS = {

    "DRAFT": {
        "PENDING_FACULTY_APPROVAL"
    },

    "PENDING_FACULTY_APPROVAL": {
        "APPROVED",
        "REJECTED"
    },

    "APPROVED": {
        "ONGOING",
        "CANCELLED"
    },

    "ONGOING": {
        "COMPLETED",
        "CANCELLED"
    },

    "COMPLETED": set(),

    "CANCELLED": set(),

    "REJECTED": {
        "PENDING_FACULTY_APPROVAL"
    }
}


def can_change_event_status(current_status, new_status):

    allowed_statuses = EVENT_STATUS_TRANSITIONS.get(
        current_status,
        set()
    )

    return new_status in allowed_statuses
# ==================================================
# EVENT SUBMISSION
# ==================================================

def submit_event_for_approval(event, user):

    # User must be logged in
    if not user.is_authenticated:
        return False, "Login required."

    # Only Club Admin can submit events
    if user.role != "CLUB_ADMIN":
        return False, "Only Club Admin can submit events."

    # Event must currently be Draft
    if event.status != "DRAFT":
        return False, "Only Draft events can be submitted."

    # User must be the creator
    if event.created_by != user.id:
        return False, "You are not the event creator."

    # Check valid transition
    if not can_change_event_status(
        event.status,
        "PENDING_FACULTY_APPROVAL"
    ):
        return False, "Invalid event status transition."

    # Move event to approval queue
    event.status = "PENDING_FACULTY_APPROVAL"

    return True, "Event submitted for Faculty approval."
# ==================================================
# FACULTY EVENT APPROVAL
# ==================================================

def faculty_decide_event(event, faculty_user, decision, rejection_reason=None):

    # User must be logged in
    if not faculty_user.is_authenticated:
        return False, "Login required."

    # Only Faculty can approve or reject
    if faculty_user.role != "FACULTY":
        return False, "Only Faculty can approve or reject events."

    # Event must be waiting for approval
    if event.status != "PENDING_FACULTY_APPROVAL":
        return False, "Event is not waiting for Faculty approval."

    # Decision must be APPROVE or REJECT
    if decision not in {"APPROVE", "REJECT"}:
        return False, "Invalid decision."

    # ----------------------------------------------
    # APPROVE
    # ----------------------------------------------

    if decision == "APPROVE":

        if not can_change_event_status(
            event.status,
            "APPROVED"
        ):
            return False, "Invalid event status transition."

        event.status = "APPROVED"
        event.rejection_reason = None

        return True, "Event approved successfully."

    # ----------------------------------------------
    # REJECT
    # ----------------------------------------------

    if decision == "REJECT":

        if not rejection_reason:
            return False, "Rejection reason is required."

        if not can_change_event_status(
            event.status,
            "REJECTED"
        ):
            return False, "Invalid event status transition."

        event.status = "REJECTED"
        event.rejection_reason = rejection_reason

        return True, "Event rejected successfully."
    # ==================================================
# STUDENT EVENT REGISTRATION
# ==================================================

def register_student_for_event(event, student_user):

    # User must be logged in
    if not student_user.is_authenticated:
        return False, "Login required."

    # Only Student can register
    if student_user.role != "STUDENT":
        return False, "Only Students can register for events."

    # Event must be approved
    if event.status != "APPROVED":
        return False, "Students can register only for approved events."

    # Get Student profile
    student = student_user.student_profile

    if not student:
        return False, "Student profile not found."

    # Import here to avoid circular imports
    from app.models import EventRegistration

    # Check duplicate registration
    existing = EventRegistration.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if existing:

        if existing.status == "REGISTERED":
            return False, "You are already registered for this event."

        # Allow re-registration after cancellation
        existing.status = "REGISTERED"
        return True, "Registration successful."

    # Check current registration count
    registered_count = EventRegistration.query.filter_by(
        event_id=event.id,
        status="REGISTERED"
    ).count()

    # Capacity check
    if registered_count >= event.capacity:
        return False, "Event capacity is full."

    # Create registration
    registration = EventRegistration(
        event_id=event.id,
        student_id=student.id,
        status="REGISTERED"
    )

    db.session.add(registration)

    return True, "Registration successful."
# ==================================================
# TIMETABLE VALIDATION
# ==================================================

def validate_timetable_periods(periods):
    """
    Validate timetable periods.

    Rules:
    1. Start time must be before end time.
    2. Periods must be in chronological order.
    3. Periods cannot overlap.
    4. Duration must be greater than zero.
    """

    if not periods:
        return False, "At least one timetable period is required."

    # Sort by start time
    sorted_periods = sorted(
        periods,
        key=lambda period: period["start_time"]
    )

    for i, period in enumerate(sorted_periods):

        start = period["start_time"]
        end = period["end_time"]

        # Rule 1
        if end <= start:
            return False, (
                f"Invalid period '{period['label']}': "
                "end time must be after start time."
            )

        # Rule 2 and 3
        if i > 0:
            previous = sorted_periods[i - 1]

            if start < previous["end_time"]:
                return False, (
                    f"Timetable overlap detected between "
                    f"'{previous['label']}' and '{period['label']}'."
                )

        # Rule 4
        duration = (
            end.hour * 60 + end.minute
            - start.hour * 60 - start.minute
        )

        if duration <= 0:
            return False, (
                f"Invalid duration for '{period['label']}'."
            )

    return True, "Timetable is valid."
def create_timetable(timetable, periods, user):
    """
    Create timetable only for Super Admin.
    """

    if not user.is_authenticated:
        return False, "Login required."

    if user.role != "SUPER_ADMIN":
        return False, "Only Super Admin can manage timetables."

    valid, message = validate_timetable_periods(periods)

    if not valid:
        return False, message

    from app.models import TimetablePeriod

    for period_data in periods:

        start = period_data["start_time"]
        end = period_data["end_time"]

        duration = (
            end.hour * 60 + end.minute
            - start.hour * 60 - start.minute
        )

        period = TimetablePeriod(
            timetable_id=timetable.id,
            period_order=period_data["period_order"],
            label=period_data["label"],
            start_time=start,
            end_time=end,
            period_type=period_data["period_type"],
            duration_minutes=duration
        )

        db.session.add(period)

    return True, "Timetable created successfully."
# ==================================================
# OD TIMETABLE PERIOD CALCULATION
# ==================================================

def calculate_affected_periods(event, timetable):
    """
    Find timetable CLASS periods affected by an event.

    A period is affected when the event time overlaps
    with the timetable period.
    """

    from app.models import TimetablePeriod

    periods = TimetablePeriod.query.filter_by(
        timetable_id=timetable.id
    ).order_by(
        TimetablePeriod.period_order
    ).all()

    affected_periods = []

    for period in periods:

        # Ignore BREAK and LUNCH
        if period.period_type != "CLASS":
            continue

        # No overlap:
        # Event ends before/equal period starts
        # OR event starts after/equal period ends
        if (
            event.end_time <= period.start_time
            or event.start_time >= period.end_time
        ):
            continue

        affected_periods.append(period)

    return affected_periods
def apply_for_od(event, student_user):
    """
    Student applies for OD for an approved event.

    Rules:
    1. Only students can apply.
    2. Event must be approved.
    3. Student must be registered for the event.
    4. Student must have a Class Mentor.
    5. One OD request per student per event.
    """

    from app.models import Student, EventRegistration, ODRequest

    # Check login
    if not student_user.is_authenticated:
        return False, "Login required.", None

    # Only STUDENT can apply
    if student_user.role != "STUDENT":
        return False, "Only students can apply for OD.", None

    # Event must be approved
    if event.status != "APPROVED":
        return False, "OD can be applied only for an approved event.", None

    # Find student profile
    student = Student.query.filter_by(
        user_id=student_user.id
    ).first()

    if not student:
        return False, "Student profile not found.", None

    # Student must have a Class Mentor
    if not student.class_mentor_id:
        return False, "Class Mentor is not assigned.", None

    # Student must already be registered
    registration = EventRegistration.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if not registration:
        return False, "You must register for the event before applying for OD.", None

    # Prevent duplicate OD request
    existing_request = ODRequest.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if existing_request:
        return False, "OD request already exists for this event.", existing_request

    # Create OD request
    od_request = ODRequest(
        student_id=student.id,
        event_id=event.id,
        mentor_id=student.class_mentor_id,
        status="PENDING"
    )

    db.session.add(od_request)
    db.session.commit()

    return True, "OD request submitted successfully.", od_request

def apply_for_od_with_periods(event, student_user, timetable):
    """
    Create an OD request and calculate the timetable
    periods affected by the event.
    """

    from app.models import Student, EventRegistration, ODRequest

    # Basic student checks
    if not student_user.is_authenticated:
        return False, "Login required.", None, []

    if student_user.role != "STUDENT":
        return False, "Only students can apply for OD.", None, []

    # Event must be approved
    if event.status != "APPROVED":
        return False, "OD can be applied only for an approved event.", None, []

    # Find student
    student = Student.query.filter_by(
        user_id=student_user.id
    ).first()

    if not student:
        return False, "Student profile not found.", None, []

    # Class Mentor is mandatory
    if not student.class_mentor_id:
        return False, "Class Mentor is not assigned.", None, []

    # Student must be registered for event
    registration = EventRegistration.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if not registration:
        return False, "Register for the event before applying for OD.", None, []

    # Prevent duplicate OD
    existing = ODRequest.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if existing:
        return False, "OD request already exists.", existing, []

    # Calculate affected class periods
    affected_periods = calculate_affected_periods(
        event,
        timetable
    )

    # Create OD request
    od_request = ODRequest(
        student_id=student.id,
        event_id=event.id,
        mentor_id=student.class_mentor_id,
        status="PENDING"
    )

    db.session.add(od_request)
    db.session.commit()

    return (
        True,
        "OD request submitted successfully.",
        od_request,
        affected_periods
    )
def decide_od_request(
    od_request,
    faculty_user,
    decision,
    rejection_reason=None,
    timetable=None
):
    """
    Class Mentor approves or rejects an OD request.

    APPROVE:
        Creates permanent timetable snapshots.

    REJECT:
        Stores the rejection reason.
    """

    from app.models import ODPeriodSnapshot, Event

    # Must be logged in
    if not faculty_user.is_authenticated:
        return False, "Login required."

    # Only Faculty can decide OD
    if faculty_user.role != "FACULTY":
        return False, "Only faculty can approve or reject OD."

    # Request must be pending
    if od_request.status != "PENDING":
        return False, "This OD request has already been decided."

    # Only the student's assigned Class Mentor can decide
    if od_request.mentor_id != faculty_user.id:
        return False, "Only the student's Class Mentor can decide this OD."

    # Validate decision
    decision = decision.upper()

    if decision not in {"APPROVE", "REJECT"}:
        return False, "Invalid decision."

    # REJECT
    if decision == "REJECT":

        if not rejection_reason or not rejection_reason.strip():
            return False, "Rejection reason is required."

        od_request.status = "REJECTED"
        od_request.decision_reason = rejection_reason.strip()
        od_request.decided_at = db.func.now()

        db.session.commit()

        return True, "OD request rejected."

    # APPROVE
    if timetable is None:
        return False, "Active timetable is required for approval."

    # Get the event using event_id
    event = db.session.get(Event, od_request.event_id)

    if not event:
        return False, "Event not found."

    # Calculate periods at the moment of approval
    affected_periods = calculate_affected_periods(
        event,
        timetable
    )

    # Create permanent historical snapshots
    for period in affected_periods:

        snapshot = ODPeriodSnapshot(
            od_request_id=od_request.id,
            timetable_period_id=period.id,
            period_order=period.period_order,
            period_label=period.label,
            start_time=period.start_time,
            end_time=period.end_time,
            duration_minutes=period.duration_minutes
        )

        db.session.add(snapshot)

    # Approve request
    od_request.status = "APPROVED"
    od_request.decided_at = db.func.now()

    db.session.commit()

    return True, "OD request approved successfully."
