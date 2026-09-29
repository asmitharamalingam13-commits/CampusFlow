from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user

from app import db
from app.models import TimetableStructure
from app.permissions import permission_required


# --------------------------------------------------
# MAIN BLUEPRINT
# --------------------------------------------------

main = Blueprint("main", __name__)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@main.route("/")
def home():
    return render_template("login.html")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@main.route("/dashboard")
@login_required
def dashboard():

    from app.models import (
        Club,
        ClubMember,
        Event,
        EventRegistration,
        ODRequest,
        Certificate
    )

    my_club = None
    club_events = []
    club_members_count = 0

    total_events = 0
    pending_events = 0
    approved_events = 0
    rejected_events = 0
    completed_events = 0

    total_registrations = 0

    total_od_requests = 0
    pending_od_requests = 0
    approved_od_requests = 0
    rejected_od_requests = 0

    total_certificates = 0

    # ==============================
    # CLUB ADMIN DASHBOARD
    # ==============================

    if current_user.role == "CLUB_ADMIN":

        # Find the club owned by this Club Admin
        my_club = Club.query.filter_by(
            club_admin_id=current_user.id
        ).first()

        if my_club:

            # ------------------------------
            # CLUB MEMBERS
            # ------------------------------

            club_members_count = ClubMember.query.filter_by(
                club_id=my_club.id
            ).count()

            # ------------------------------
            # EVENTS
            # ------------------------------

            club_events = Event.query.filter_by(
                club_id=my_club.id
            ).all()

            total_events = len(club_events)

            pending_events = sum(
                1 for e in club_events
                if e.status == "DRAFT"
            )

            approved_events = sum(
                1 for e in club_events
                if e.status == "APPROVED"
            )

            rejected_events = sum(
                1 for e in club_events
                if e.status == "REJECTED"
            )

            completed_events = sum(
                1 for e in club_events
                if e.status == "COMPLETED"
            )

            # ------------------------------
            # EVENT REGISTRATIONS
            # ------------------------------

            event_ids = [e.id for e in club_events]

            if event_ids:

                total_registrations = (
                    EventRegistration.query
                    .filter(
                        EventRegistration.event_id.in_(event_ids)
                    )
                    .count()
                )

            # ------------------------------
            # OD REQUESTS
            # ------------------------------

            member_student_ids = [
                m.student_id
                for m in ClubMember.query.filter_by(
                    club_id=my_club.id
                ).all()
            ]

            if member_student_ids:

                total_od_requests = (
                    ODRequest.query
                    .filter(
                        ODRequest.student_id.in_(member_student_ids)
                    )
                    .count()
                )

                pending_od_requests = (
                    ODRequest.query
                    .filter(
                        ODRequest.student_id.in_(member_student_ids),
                        ODRequest.status == "PENDING"
                    )
                    .count()
                )

                approved_od_requests = (
                    ODRequest.query
                    .filter(
                        ODRequest.student_id.in_(member_student_ids),
                        ODRequest.status == "APPROVED"
                    )
                    .count()
                )

                rejected_od_requests = (
                    ODRequest.query
                    .filter(
                        ODRequest.student_id.in_(member_student_ids),
                        ODRequest.status == "REJECTED"
                    )
                    .count()
                )

            # ------------------------------
            # CERTIFICATES
            # ------------------------------

            if event_ids:

                total_certificates = (
                    Certificate.query
                    .filter(
                        Certificate.event_id.in_(event_ids)
                    )
                    .count()
                )

    # ==============================
    # SEND DATA TO DASHBOARD
    # ==============================

    return render_template(
        "dashboard.html",

        user=current_user,

        my_club=my_club,
        club_members_count=club_members_count,
        club_events=club_events,

        total_events=total_events,
        pending_events=pending_events,
        approved_events=approved_events,
        rejected_events=rejected_events,
        completed_events=completed_events,

        total_registrations=total_registrations,

        total_od_requests=total_od_requests,
        pending_od_requests=pending_od_requests,
        approved_od_requests=approved_od_requests,
        rejected_od_requests=rejected_od_requests,

        total_certificates=total_certificates
    )
# --------------------------------------------------
# RBAC TEST ROUTE
# --------------------------------------------------

@main.route("/admin-test")
@login_required
@permission_required("manage_users")
def admin_test():

    return "SUCCESS: You have permission to manage users."


# --------------------------------------------------
# STUDENT OD APPLICATION
# --------------------------------------------------

@main.route("/student/od", methods=["GET", "POST"])
@login_required
def student_od():

    from app.models import Student, Event
    from app.permissions import apply_for_od_with_periods

    user = current_user

    # --------------------------------------------------
    # Only students can access this page
    # --------------------------------------------------

    if user.role != "STUDENT":
        return "Only students can access this page.", 403

    # --------------------------------------------------
    # Find student profile
    # --------------------------------------------------

    student = Student.query.filter_by(
        user_id=user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    # --------------------------------------------------
    # Get approved events
    # --------------------------------------------------

    events = Event.query.filter_by(
        status="APPROVED"
    ).all()

    message = None

    # --------------------------------------------------
    # Handle OD application
    # --------------------------------------------------

    if request.method == "POST":

        event_id = request.form.get("event_id")

        if not event_id:
            message = "Please select an event."

        else:

            try:
                event = db.session.get(
                    Event,
                    int(event_id)
                )
            except (ValueError, TypeError):
                event = None

            # --------------------------------------------------
            # Check event
            # --------------------------------------------------

            if not event:
                message = "Event not found."

            else:

                # --------------------------------------------------
                # Get active timetable
                # --------------------------------------------------

                timetable = TimetableStructure.query.filter_by(
                    is_active=True
                ).first()

                if not timetable:

                    message = "No active timetable is available."

                else:

                    # --------------------------------------------------
                    # Apply for OD
                    #
                    # Function expects:
                    # 1. event
                    # 2. logged-in student user
                    # 3. timetable
                    #
                    # Function returns:
                    # 1. success
                    # 2. message
                    # 3. OD request
                    # 4. affected periods
                    # --------------------------------------------------

                    (
                        success,
                        msg,
                        od_request,
                        affected_periods
                    ) = apply_for_od_with_periods(
                        event,
                        user,
                        timetable
                    )

                    message = msg

    # --------------------------------------------------
    # Display page
    # --------------------------------------------------

    return render_template(
        "student_od.html",
        events=events,
        message=message
    )
# --------------------------------------------------
# FACULTY OD APPROVAL
# --------------------------------------------------

@main.route("/faculty/od", methods=["GET"])
@login_required
def faculty_od():

    from app.models import ODRequest, Student, Event

    # --------------------------------------------------
    # Only Faculty can access this page
    # --------------------------------------------------

    if current_user.role != "FACULTY":
        return "Only faculty can access this page.", 403

    # --------------------------------------------------
    # Get OD requests assigned to this Class Mentor
    # --------------------------------------------------

    od_requests = ODRequest.query.filter_by(
        mentor_id=current_user.id
    ).order_by(
        ODRequest.requested_at.desc()
    ).all()

    # --------------------------------------------------
    # Prepare student and event information
    # --------------------------------------------------

    requests_data = []

    for od in od_requests:

        student = db.session.get(
            Student,
            od.student_id
        )

        event = db.session.get(
            Event,
            od.event_id
        )

        requests_data.append({
            "od": od,
            "student": student,
            "event": event
        })

    # --------------------------------------------------
    # Display Faculty OD page
    # --------------------------------------------------

    return render_template(
        "faculty_od.html",
        requests_data=requests_data
    )
# --------------------------------------------------
# APPROVE OD REQUEST
# --------------------------------------------------

@main.route("/faculty/od/<int:od_id>/approve", methods=["POST"])
@login_required
def approve_od(od_id):

    from app.models import ODRequest
    from app.permissions import decide_od_request

    # --------------------------------------------------
    # Only Faculty can approve
    # --------------------------------------------------

    if current_user.role != "FACULTY":
        return "Only faculty can approve OD requests.", 403

    # --------------------------------------------------
    # Find OD request
    # --------------------------------------------------

    od_request = db.session.get(
        ODRequest,
        od_id
    )

    if not od_request:
        return "OD request not found.", 404

    # --------------------------------------------------
    # Get active timetable
    # --------------------------------------------------

    timetable = TimetableStructure.query.filter_by(
        is_active=True
    ).first()

    if not timetable:
        return "No active timetable is available.", 400

    # --------------------------------------------------
    # Approve OD
    # --------------------------------------------------

    success, message = decide_od_request(
        od_request,
        current_user,
        "APPROVE",
        timetable=timetable
    )

    if not success:
        return message, 400

    return """
    <h2>OD Approved Successfully</h2>
    <p>{}</p>
    <p><a href="/faculty/od">Back to Faculty OD</a></p>
    """.format(message)


# --------------------------------------------------
# REJECT OD REQUEST
# --------------------------------------------------

@main.route("/faculty/od/<int:od_id>/reject", methods=["POST"])
@login_required
def reject_od(od_id):

    from app.models import ODRequest
    from app.permissions import decide_od_request

    # --------------------------------------------------
    # Only Faculty can reject
    # --------------------------------------------------

    if current_user.role != "FACULTY":
        return "Only faculty can reject OD requests.", 403

    # --------------------------------------------------
    # Find OD request
    # --------------------------------------------------

    od_request = db.session.get(
        ODRequest,
        od_id
    )

    if not od_request:
        return "OD request not found.", 404

    # --------------------------------------------------
    # Get rejection reason
    # --------------------------------------------------

    rejection_reason = request.form.get(
        "rejection_reason",
        ""
    ).strip()

    if not rejection_reason:
        return "Rejection reason is required.", 400

    # --------------------------------------------------
    # Reject OD
    # --------------------------------------------------

    success, message = decide_od_request(
        od_request,
        current_user,
        "REJECT",
        rejection_reason=rejection_reason
    )

    if not success:
        return message, 400

    return """
    <h2>OD Rejected</h2>
    <p>{}</p>
    <p><a href="/faculty/od">Back to Faculty OD</a></p>
    """.format(message)
@main.route("/student/od/status", methods=["GET"])
@login_required
def student_od_status():
    from app.models import (
        Student,
        ODRequest,
        Event,
        ODPeriodSnapshot
    )

    if current_user.role != "STUDENT":
        return "Only students can access this page.", 403

    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    od_requests = ODRequest.query.filter_by(
        student_id=student.id
    ).order_by(
        ODRequest.requested_at.desc()
    ).all()

    requests_data = []

    for od in od_requests:

        event = db.session.get(
            Event,
            od.event_id
        )

        snapshots = ODPeriodSnapshot.query.filter_by(
            od_request_id=od.id
        ).order_by(
            ODPeriodSnapshot.period_order
        ).all()

        requests_data.append({
            "od": od,
            "event": event,
            "snapshots": snapshots
        })

    return render_template(
        "student_od_status.html",
        requests_data=requests_data
    )
@main.route("/faculty/attendance/<int:event_id>", methods=["GET"])
@login_required
def faculty_attendance(event_id):
    from app.models import Event, EventRegistration, Student, Attendance

    # Only faculty can mark attendance
    if current_user.role != "FACULTY":
        return "Only faculty can access attendance.", 403

    # Find event
    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Get all registered students
    registrations = EventRegistration.query.filter_by(
        event_id=event.id,
        status="REGISTERED"
    ).all()

    students_data = []

    for registration in registrations:

        student = db.session.get(
            Student,
            registration.student_id
        )

        attendance = Attendance.query.filter_by(
            event_id=event.id,
            student_id=student.id
        ).first()

        students_data.append({
            "student": student,
            "attendance": attendance
        })

    return render_template(
        "faculty_attendance.html",
        event=event,
        students_data=students_data
    )

@main.route(
    "/faculty attendance/<int:event_id>/<int:student_id>",
    methods=["POST"]
)
@login_required
def mark_attendance(event_id, student_id):

    from app.models import (
        Event,
        Student,
        EventRegistration,
        Attendance,
        ODRequest
    )

    import secrets

    # ---------------------------------------------------------
    # ONLY FACULTY CAN MARK ATTENDANCE
    # ---------------------------------------------------------

    if current_user.role != "FACULTY":
        return "Only faculty can mark attendance.", 403

    # ---------------------------------------------------------
    # CHECK EVENT
    # ---------------------------------------------------------

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # ---------------------------------------------------------
    # CHECK STUDENT
    # ---------------------------------------------------------

    student = db.session.get(Student, student_id)

    if not student:
        return "Student not found.", 404

    # ---------------------------------------------------------
    # CHECK STUDENT REGISTRATION
    # ---------------------------------------------------------

    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=student_id,
        status="REGISTERED"
    ).first()

    if not registration:
        return (
            "Student is not registered for this event. "
            "Attendance cannot be marked.",
            400
        )

    # ---------------------------------------------------------
    # MARK ATTENDANCE AS PRESENT
    # ---------------------------------------------------------

    attendance = Attendance.query.filter_by(
        event_id=event_id,
        student_id=student_id
    ).first()

    if attendance:
        attendance.status = "PRESENT"
    else:
        attendance = Attendance(
            event_id=event_id,
            student_id=student_id,
            status="PRESENT"
        )

        db.session.add(attendance)

    # ---------------------------------------------------------
    # FIND OD REQUEST
    # ---------------------------------------------------------

    od_request = ODRequest.query.filter_by(
        event_id=event_id,
        student_id=student_id
    ).first()

    if not od_request:
        return (
            "OD request not found. "
            "The student must register for the event first.",
            400
        )

    # ---------------------------------------------------------
    # APPROVE OD ONLY AFTER PRESENT
    # ---------------------------------------------------------

    od_request.status = "APPROVED"

    od_request.decision_reason = (
        "Automatically approved because faculty "
        "marked the student PRESENT at the event."
    )

    od_request.decided_at = db.func.now()

    # ---------------------------------------------------------
    # GENERATE APPROVAL CODE
    # ---------------------------------------------------------

    if not od_request.approval_code:

        # Generate secure random code
        approval_code = (
            "OD-"
            + secrets.token_hex(4).upper()
        )

        # Make sure code is unique
        while ODRequest.query.filter_by(
            approval_code=approval_code
        ).first():

            approval_code = (
                "OD-"
                + secrets.token_hex(4).upper()
            )

        od_request.approval_code = approval_code

    # ---------------------------------------------------------
    # SAVE EVERYTHING
    # ---------------------------------------------------------

    db.session.commit()

    # ---------------------------------------------------------
    # SUCCESS
    # ---------------------------------------------------------

    return f"""
    <h2>Attendance Marked Successfully ✅</h2>

    <p>
        Student:
        <strong>{student.user.name}</strong>
    </p>

    <p>
        Attendance:
        <strong>PRESENT</strong>
    </p>

    <p>
        OD Status:
        <strong>APPROVED</strong>
    </p>

    <p>
        Approval Code:
        <strong style="font-size:22px;">
            {od_request.approval_code}
        </strong>
    </p>

    <p>
        This approval code was generated because
        the faculty marked the registered student
        as PRESENT.
    </p>

    <p>
        <a href="/faculty/attendance/{event_id}">
            Back to Attendance
        </a>
    </p>
    """

    # ---------------------------------------------------------
    # ONLY FACULTY CAN MARK ATTENDANCE
    # ---------------------------------------------------------

    if current_user.role != "FACULTY":
        return "Only faculty can mark attendance.", 403

    # ---------------------------------------------------------
    # CHECK EVENT
    # ---------------------------------------------------------

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # ---------------------------------------------------------
    # CHECK STUDENT
    # ---------------------------------------------------------

    student = db.session.get(Student, student_id)

    if not student:
        return "Student not found.", 404

    # ---------------------------------------------------------
    # CHECK STUDENT REGISTRATION
    # ---------------------------------------------------------

    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=student_id,
        status="REGISTERED"
    ).first()

    if not registration:
        return "Student is not registered for this event.", 400

    # ---------------------------------------------------------
    # MARK ATTENDANCE
    # ---------------------------------------------------------

    attendance = Attendance.query.filter_by(
        event_id=event_id,
        student_id=student_id
    ).first()

    if attendance:
        attendance.status = "PRESENT"
    else:
        attendance = Attendance(
            event_id=event_id,
            student_id=student_id,
            status="PRESENT"
        )

        db.session.add(attendance)

    # ---------------------------------------------------------
    # AUTOMATICALLY APPROVE OD
    # ---------------------------------------------------------

    od_request = ODRequest.query.filter_by(
        event_id=event_id,
        student_id=student_id
    ).first()

    if od_request:

        od_request.status = "APPROVED"

        od_request.decision_reason = (
            "Automatically approved because "
            "faculty marked the student PRESENT."
        )

    # Save attendance + OD approval together
    db.session.commit()

    # ---------------------------------------------------------
    # SUCCESS MESSAGE
    # --------

@main.route(
    "/faculty/event/<int:event_id>/generate-certificates",
    methods=["POST"]
)
@login_required
def generate_certificates(event_id):
    from app.models import (
        Event,
        EventRegistration,
        Student,
        Attendance,
        Certificate
    )

    import os
    import uuid
    import qrcode

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    # Only faculty can generate certificates
    if current_user.role != "FACULTY":
        return "Only faculty can generate certificates.", 403

    # Find event
    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Event must be completed
    if event.status != "COMPLETED":
        return "Complete the event before generating certificates.", 400

    # Certificate folder
    certificate_folder = os.path.join(
        "app",
        "static",
        "certificates"
    )

    os.makedirs(
        certificate_folder,
        exist_ok=True
    )

    # Get registered students
    registrations = EventRegistration.query.filter_by(
        event_id=event.id,
        status="REGISTERED"
    ).all()

    generated = 0

    for registration in registrations:

        student = db.session.get(
            Student,
            registration.student_id
        )

        if not student:
            continue

        # Student must be PRESENT
        attendance = Attendance.query.filter_by(
            event_id=event.id,
            student_id=student.id,
            status="PRESENT"
        ).first()

        if not attendance:
            continue

        # Avoid duplicate certificate
        existing = Certificate.query.filter_by(
            event_id=event.id,
            student_id=student.id
        ).first()

        if existing:
            continue

        # Generate unique certificate ID
        certificate_id = "CERT-" + uuid.uuid4().hex[:10].upper()

        # PDF filename
        filename = f"{certificate_id}.pdf"

        file_path = os.path.join(
            certificate_folder,
            filename
        )

        # Create QR code
        qr_data = f"CampusFlow Certificate: {certificate_id}"

        qr = qrcode.make(qr_data)

        qr_path = os.path.join(
            certificate_folder,
            f"{certificate_id}_qr.png"
        )

        qr.save(qr_path)

        # Create PDF
        pdf = canvas.Canvas(
            file_path,
            pagesize=A4
        )

        width, height = A4

        pdf.setFont(
            "Helvetica-Bold",
            28
        )

        pdf.drawCentredString(
            width / 2,
            height - 120,
            "CERTIFICATE OF PARTICIPATION"
        )

        pdf.setFont(
            "Helvetica",
            16
        )

        pdf.drawCentredString(
            width / 2,
            height - 190,
            "This certificate is proudly presented to"
        )

        pdf.setFont(
            "Helvetica-Bold",
            24
        )

        pdf.drawCentredString(
            width / 2,
            height - 240,
            student.user.name
        )

        pdf.setFont(
            "Helvetica",
            15
        )

        pdf.drawCentredString(
            width / 2,
            height - 290,
            f"for participating in {event.title}"
        )

        pdf.drawCentredString(
            width / 2,
            height - 320,
            f"Event Date: {event.event_date}"
        )

        pdf.setFont(
            "Helvetica",
            11
        )

        pdf.drawString(
            60,
            70,
            f"Certificate ID: {certificate_id}"
        )

        pdf.drawImage(
            qr_path,
            width - 150,
            45,
            width=90,
            height=90
        )

        pdf.save()

        # Save certificate record
        certificate = Certificate(
            event_id=event.id,
            student_id=student.id,
            certificate_id=certificate_id,
            file_path=file_path
        )

        db.session.add(certificate)

        generated += 1

    db.session.commit()

    return f"""
    <h2>Certificates Generated Successfully</h2>

    <p>
        Event: <strong>{event.title}</strong>
    </p>

    <p>
        Certificates generated:
        <strong>{generated}</strong>
    </p>

    <p>
        Only students marked PRESENT received certificates.
    </p>

    <p>
        <a href="/dashboard">
            Back to Dashboard
        </a>
    </p>
    """
@main.route("/student/certificates")
@login_required
def student_certificates():
    from app.models import Student, Certificate, Event

    # Only students can access this page
    if current_user.role != "STUDENT":
        return "Only students can access certificates.", 403

    # Find student profile
    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    # Get certificates belonging to this student
    certificates = Certificate.query.filter_by(
        student_id=student.id
    ).order_by(
        Certificate.issued_at.desc()
    ).all()

    certificates_data = []

    for certificate in certificates:

        event = db.session.get(
            Event,
            certificate.event_id
        )

        certificates_data.append({
            "certificate": certificate,
            "event": event
        })

    return render_template(
        "student_certificates.html",
        certificates_data=certificates_data
    )
@main.route(
    "/student/certificates/<int:certificate_id>/download"
)
@login_required
def download_certificate(certificate_id):
    from app.models import Certificate, Student
    from flask import send_file
    import os

    # Only students can download certificates
    if current_user.role != "STUDENT":
        return "Only students can download certificates.", 403

    # Find student profile
    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    # Find certificate
    certificate = db.session.get(
        Certificate,
        certificate_id
    )

    if not certificate:
        return "Certificate not found.", 404

    # Security check:
    # Student can download only their own certificate
    if certificate.student_id != student.id:
        return "You are not allowed to access this certificate.", 403

    # Check PDF exists
    if not certificate.file_path:
        return "Certificate file not available.", 404

    if not os.path.exists(certificate.file_path):
        return "Certificate PDF not found.", 404

    return send_file(
        certificate.file_path,
        as_attachment=True,
        download_name=f"{certificate.certificate_id}.pdf"
    )
@main.route("/club-admin/events/create", methods=["GET", "POST"])
@login_required
def create_event():
    from datetime import datetime
    from app.models import Event, Club

    # Only Club Admin can create events
    if current_user.role != "CLUB_ADMIN":
        return "Only Club Admin can create events.", 403

    # Find the club managed by this Club Admin
    club = Club.query.filter_by(
        club_admin_id=current_user.id
    ).first()

    if not club:
        return "No club is assigned to this Club Admin.", 404

    message = None

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        event_date = request.form.get("event_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        venue = request.form.get("venue", "").strip()
        capacity = request.form.get("capacity")

        # Basic validation
        if not all([
            title,
            event_date,
            start_time,
            end_time,
            venue,
            capacity
        ]):
            message = "Please fill all required fields."

        else:
            try:
                event_date_value = datetime.strptime(
                    event_date,
                    "%Y-%m-%d"
                ).date()

                start_time_value = datetime.strptime(
                    start_time,
                    "%H:%M"
                ).time()

                end_time_value = datetime.strptime(
                    end_time,
                    "%H:%M"
                ).time()

                capacity_value = int(capacity)

                if start_time_value >= end_time_value:
                    message = "End time must be after start time."

                elif capacity_value <= 0:
                    message = "Capacity must be greater than zero."

                else:
                    event = Event(
                        club_id=club.id,
                        title=title,
                        description=description,
                        event_date=event_date_value,
                        start_time=start_time_value,
                        end_time=end_time_value,
                        venue=venue,
                        capacity=capacity_value,

                        # Important:
                        # New events start as DRAFT.
                        status="DRAFT",

                        created_by=current_user.id
                    )

                    db.session.add(event)
                    db.session.commit()

                    return f"""
                    <h2>Event Created Successfully</h2>

                    <p>
                        Event:
                        <strong>{event.title}</strong>
                    </p>

                    <p>
                        Status:
                        <strong>DRAFT</strong>
                    </p>

                    <p>
                        The event must be approved by Faculty
                        before students can register.
                    </p>

                    <p>
                        <a href="/dashboard">
                            Back to Dashboard
                        </a>
                    </p>
                    """

            except (ValueError, TypeError):
                message = "Please enter valid date, time and capacity."

    return render_template(
        "club_admin_create_event.html",
        club=club,
        message=message
    )
@main.route("/faculty/events", methods=["GET"])
@login_required
def faculty_events():

    from app.models import Event

    if current_user.role != "FACULTY":
        return "Only faculty can access event approvals.", 403

    # Events waiting for faculty approval
    events = Event.query.filter_by(
        status="DRAFT"
    ).order_by(
        Event.created_at.desc()
    ).all()

    # Events already approved
    approved_events = Event.query.filter_by(
        status="APPROVED"
    ).order_by(
        Event.event_date.asc()
    ).all()

    return render_template(
        "faculty_events.html",
        events=events,
        approved_events=approved_events
    )
@main.route("/faculty/events/<int:event_id>/approve", methods=["POST"])
@login_required
def approve_event(event_id):
    from app.models import Event

    if current_user.role != "FACULTY":
        return "Only faculty can approve events.", 403

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    if event.status != "DRAFT":
        return "Only DRAFT events can be approved.", 400

    event.status = "APPROVED"
    event.rejection_reason = None

    db.session.commit()

    return f"""
    <h2>Event Approved Successfully</h2>
    <p>Event: <strong>{event.title}</strong></p>
    <p>Status: <strong>APPROVED</strong></p>
    <p>Students can now register for this event.</p>
    <p><a href="/faculty/events">Back to Faculty Events</a></p>
    """
@main.route("/faculty/events/<int:event_id>/reject", methods=["POST"])
@login_required
def reject_event(event_id):
    from app.models import Event

    if current_user.role != "FACULTY":
        return "Only faculty can reject events.", 403

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    if event.status != "DRAFT":
        return "Only DRAFT events can be rejected.", 400

    reason = request.form.get("rejection_reason", "").strip()

    if not reason:
        return "Rejection reason is required.", 400

    event.status = "REJECTED"
    event.rejection_reason = reason

    db.session.commit()

    return f"""
    <h2>Event Rejected</h2>
    <p>Event: <strong>{event.title}</strong></p>
    <p>Reason: <strong>{reason}</strong></p>
    <p>Status: <strong>REJECTED</strong></p>
    <p><a href="/faculty/events">Back to Faculty Events</a></p>
    """
@main.route("/student/events", methods=["GET"])
@login_required
def student_events():
    from app.models import Event, EventRegistration, Student

    if current_user.role != "STUDENT":
        return "Only students can access events.", 403

    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    events = Event.query.filter_by(
        status="APPROVED"
    ).order_by(Event.event_date.asc()).all()

    registered_event_ids = {
        registration.event_id
        for registration in EventRegistration.query.filter_by(
            student_id=student.id
        ).all()
    }

    return render_template(
        "student_events.html",
        events=events,
        registered_event_ids=registered_event_ids
    )


@main.route(
    "/student/events/<int:event_id>/register",
    methods=["POST"]
)
@login_required
def register_event(event_id):
    from app.models import (
    Event,
    EventRegistration,
    Student,
    ODRequest,
    Notification
)


    # Only students can register
    if current_user.role != "STUDENT":
        return "Only students can register for events.", 403

    # Get student profile
    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        return "Student profile not found.", 404

    # Get event
    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Students can register only for APPROVED events
    if event.status != "APPROVED":
        return "Students can register only for approved events.", 400

    # Check duplicate registration
    existing = EventRegistration.query.filter_by(
        event_id=event.id,
        student_id=student.id
    ).first()

    if existing:
        return "You are already registered for this event.", 400

    # Check event capacity
    registered_count = EventRegistration.query.filter_by(
        event_id=event.id,
        status="REGISTERED"
    ).count()

    if registered_count >= event.capacity:
        return "Event registration is full.", 400

    # ---------------------------------------------------------
    # CHECK CLASS MENTOR
    # ---------------------------------------------------------

    if not student.class_mentor_id:
        return (
            "Your Class Mentor is not assigned. "
            "Please contact the administrator.",
            400
        )

    # ---------------------------------------------------------
    # CREATE EVENT REGISTRATION
    # ---------------------------------------------------------

    registration = EventRegistration(
        event_id=event.id,
        student_id=student.id,
        status="REGISTERED"
    )

    db.session.add(registration)

    # ---------------------------------------------------------
    # CREATE OD REQUEST AUTOMATICALLY
    # ---------------------------------------------------------

    od_request = ODRequest(
        student_id=student.id,
        event_id=event.id,
        mentor_id=student.class_mentor_id,
        status="PENDING",
        reason="Automatically created from event registration."
    )

    db.session.add(od_request)

    # ---------------------------------------------------------
    # SEND NOTIFICATION TO CLASS MENTOR
    # ---------------------------------------------------------

    notification = Notification(
        user_id=student.class_mentor_id,
        event_id=event.id,
        student_id=student.id,
        message=(
            f"{student.user.name} "
            f"({student.ra_number}) registered for "
            f"{event.title}."
        ),
        is_read=False
    )

    db.session.add(notification)

    # ---------------------------------------------------------
    # SAVE EVERYTHING TO DATABASE
    # ---------------------------------------------------------

    db.session.commit()

    # ---------------------------------------------------------
    # SUCCESS MESSAGE
    # ---------------------------------------------------------

    return f"""
    <h2>Registration Successful 🎉</h2>

    <p>
        You are successfully registered for:
        <strong>{event.title}</strong>
    </p>

    <p>
        Event Date:
        <strong>{event.event_date}</strong>
    </p>

    <p>
        Venue:
        <strong>{event.venue}</strong>
    </p>

    <p>
        Registration Status:
        <strong>REGISTERED</strong>
    </p>

    <p>
        OD Status:
        <strong>PENDING</strong>
    </p>

    <p>
        Your Class Mentor will verify your attendance.
    </p>

    <p>
        Once the faculty marks you as
        <strong>PRESENT</strong>,
        your OD will automatically be
        <strong>APPROVED</strong>.
    </p>

    <p>
        <a href="/student/events">
            Back to Events
        </a>
        |
        <a href="/student/od/status">
            View OD Status
        </a>
    </p>
    """

# =========================================================
# CLUB ADMIN - DYNAMIC ROLE MANAGEMENT
# =========================================================

@main.route("/club-admin/roles", methods=["GET", "POST"])
@login_required
def club_admin_roles():
    from app.models import Club, ClubRole, ClubMember, ClubMemberRole, Student

    if current_user.role != "CLUB_ADMIN":
        return "Only Club Admin can manage club roles.", 403

    # Find the club managed by this Club Admin
    club = Club.query.filter_by(
        club_admin_id=current_user.id
    ).first()

    if not club:
        return "No club is assigned to this Club Admin.", 404

    message = None

    # Create a new dynamic role
    if request.method == "POST":
        role_name = request.form.get("role_name", "").strip()
        description = request.form.get("description", "").strip()

        if not role_name:
            message = "Role name is required."

        elif ClubRole.query.filter_by(
            club_id=club.id,
            name=role_name
        ).first():
            message = "This role already exists."

        else:
            role = ClubRole(
                club_id=club.id,
                name=role_name,
                description=description
            )

            db.session.add(role)
            db.session.commit()

            message = f"Role '{role_name}' created successfully."

    # Get all roles of this club
    roles = ClubRole.query.filter_by(
        club_id=club.id
    ).order_by(ClubRole.name.asc()).all()

    # Get all members of this club
    members = ClubMember.query.filter_by(
        club_id=club.id
    ).all()

    members_data = []

    for member in members:
        student = db.session.get(
            Student,
            member.student_id
        )

        assigned_roles = ClubMemberRole.query.filter_by(
            club_member_id=member.id
        ).all()

        role_names = []

        for assignment in assigned_roles:
            role = db.session.get(
                ClubRole,
                assignment.club_role_id
            )

            if role:
                role_names.append(role.name)

        members_data.append({
            "member": member,
            "student": student,
            "roles": role_names
        })

    return render_template(
        "club_admin_roles.html",
        club=club,
        roles=roles,
        members_data=members_data,
        message=message
    )
# ==================================================
# CLUB ADMIN - ROLE PERMISSION MANAGEMENT
# ==================================================

@main.route(
    "/club-admin/roles/<int:role_id>/permissions",
    methods=["GET", "POST"]
)
@login_required
def manage_role_permissions(role_id):

    from app.models import (
        Club,
        ClubRole,
        ClubRolePermission
    )

    from app.permissions import DYNAMIC_CLUB_PERMISSIONS

    # Only Club Admin can manage dynamic permissions
    if current_user.role != "CLUB_ADMIN":
        return (
            "403 Forbidden: Only Club Admin can manage permissions.",
            403
        )

    # Find club managed by this Club Admin
    club = Club.query.filter_by(
        club_admin_id=current_user.id
    ).first()

    if not club:
        return "No club is assigned to this Club Admin.", 404

    # Find requested role
    role = db.session.get(
        ClubRole,
        role_id
    )

    if not role:
        return "Role not found.", 404

    # Make sure the role belongs to this Club Admin's club
    if role.club_id != club.id:
        return "403 Forbidden: This role does not belong to your club.", 403

    # ----------------------------------------------
    # SAVE PERMISSIONS
    # ----------------------------------------------

    if request.method == "POST":

        selected_permissions = request.form.getlist(
            "permissions"
        )

        # Remove old permissions
        ClubRolePermission.query.filter_by(
            club_role_id=role.id
        ).delete()

        # Add selected permissions
        for permission in selected_permissions:

            if permission not in DYNAMIC_CLUB_PERMISSIONS:
                continue

            role_permission = ClubRolePermission(
                club_role_id=role.id,
                permission=permission
            )

            db.session.add(role_permission)

        db.session.commit()

        return redirect(
            f"/club-admin/roles/{role.id}/permissions"
        )

    # ----------------------------------------------
    # GET EXISTING PERMISSIONS
    # ----------------------------------------------

    existing_permissions = ClubRolePermission.query.filter_by(
        club_role_id=role.id
    ).all()

    selected_permissions = {
        item.permission
        for item in existing_permissions
    }

    return render_template(
        "club_role_permissions.html",
        club=club,
        role=role,
        permissions=DYNAMIC_CLUB_PERMISSIONS,
        selected_permissions=selected_permissions
    )
# =========================================================
# CLUB ADMIN - ASSIGN DYNAMIC ROLE
# =========================================================

@main.route("/club-admin/roles/assign", methods=["POST"])
@login_required
def assign_club_role():
    from app.models import (
        Club,
        ClubRole,
        ClubMember,
        ClubMemberRole
    )

    if current_user.role != "CLUB_ADMIN":
        return "Only Club Admin can assign club roles.", 403

    club = Club.query.filter_by(
        club_admin_id=current_user.id
    ).first()

    if not club:
        return "No club is assigned to this Club Admin.", 404

    member_id = request.form.get("member_id")
    role_id = request.form.get("role_id")

    try:
        member_id = int(member_id)
        role_id = int(role_id)
    except (ValueError, TypeError):
        return "Invalid member or role.", 400

    # Make sure the member belongs to this club
    member = ClubMember.query.filter_by(
        id=member_id,
        club_id=club.id
    ).first()

    if not member:
        return "Club member not found.", 404

    # Make sure the role belongs to this club
    role = ClubRole.query.filter_by(
        id=role_id,
        club_id=club.id
    ).first()

    if not role:
        return "Club role not found.", 404

    # Prevent duplicate assignment
    existing = ClubMemberRole.query.filter_by(
        club_member_id=member.id,
        club_role_id=role.id
    ).first()

    if existing:
        return "This role is already assigned to this member.", 400

    assignment = ClubMemberRole(
        club_member_id=member.id,
        club_role_id=role.id
    )

    db.session.add(assignment)
    db.session.commit()

    return f"""
    <h2>Role Assigned Successfully ✅</h2>

    <p>
        Role:
        <strong>{role.name}</strong>
    </p>

    <p>
        The role has been assigned successfully.
    </p>

    <p>
        <a href="/club-admin/roles">
            Back to Club Role Management
        </a>
    </p>
    """

# =========================================================
# DYNAMIC ROLE PERMISSION TEST
# =========================================================
# =========================================================
# DYNAMIC ROLE PERMISSION TEST
# =========================================================

@main.route("/club/event-coordinator")
@login_required
def event_coordinator_page():

    from app.models import Club
    from app.permissions import has_club_role

    # Find the club
    club = Club.query.filter_by(
        name="Tech Innovation Club"
    ).first()

    if not club:
        return "Club not found.", 404

    # Check dynamic Event Coordinator role
    allowed = has_club_role(
        current_user,
        club.id,
        "Event Coordinator"
    )

    # Deny access if role is not assigned
    if not allowed:
        return """
        <h2>403 Forbidden</h2>

        <p>
            You do not have the Event Coordinator role
            for this club.
        </p>

        <p>
            This permission was checked on the server.
        </p>

        <a href="/dashboard">
            ← Back to Dashboard
        </a>
        """, 403

    # Access granted
    return """
    <h2>Event Coordinator Access Granted ✅</h2>

    <p>
        Your dynamic club role allows you to access
        this event-management area.
    </p>

    <p>
        Role: <strong>Event Coordinator</strong>
    </p>

    <p>
        Club: <strong>Tech Innovation Club</strong>
    </p>

    <p>
        This permission was checked on the server.
    </p>

    <hr>

    <h3>Event Management</h3>

    <p>
        Create a new club event.
        The event will be created as
        <strong>DRAFT</strong>.
    </p>

    <a href="/club/event-coordinator/events/create">
        📅 Create Club Event
    </a>

    <br><br>

    <a href="/dashboard">
        ← Back to Dashboard
    </a>
    """


# =========================================================
# EVENT COORDINATOR - CREATE EVENT
# =========================================================
# =========================================================
# EVENT COORDINATOR - CREATE EVENT
# =========================================================

@main.route("/club/event-coordinator/events/create", methods=["GET", "POST"])
@login_required
def event_coordinator_create_event():

    from datetime import datetime
    from app.models import Club, Event
    from app.permissions import has_club_role

    # Find the club
    club = Club.query.filter_by(
        name="Tech Innovation Club"
    ).first()

    if not club:
        return "Club not found.", 404

    # Server-side dynamic role check
    if not has_club_role(
        current_user,
        club.id,
        "Event Coordinator"
    ):
        return "You do not have Event Coordinator permission.", 403

    message = None

    if request.method == "POST":

        title = request.form.get(
            "title", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        event_date = request.form.get(
            "event_date"
        )

        start_time = request.form.get(
            "start_time"
        )

        end_time = request.form.get(
            "end_time"
        )

        venue = request.form.get(
            "venue", ""
        ).strip()

        capacity = request.form.get(
            "capacity"
        )

        if not all([
            title,
            event_date,
            start_time,
            end_time,
            venue,
            capacity
        ]):

            message = "Please fill all required fields."

        else:

            try:

                event_date_value = datetime.strptime(
                    event_date,
                    "%Y-%m-%d"
                ).date()

                start_time_value = datetime.strptime(
                    start_time,
                    "%H:%M"
                ).time()

                end_time_value = datetime.strptime(
                    end_time,
                    "%H:%M"
                ).time()

                capacity_value = int(capacity)

                if start_time_value >= end_time_value:

                    message = "End time must be after start time."

                elif capacity_value <= 0:

                    message = "Capacity must be greater than zero."

                else:

                    # Event starts as DRAFT
                    event = Event(
                        club_id=club.id,
                        title=title,
                        description=description,
                        event_date=event_date_value,
                        start_time=start_time_value,
                        end_time=end_time_value,
                        venue=venue,
                        capacity=capacity_value,
                        status="DRAFT",
                        created_by=current_user.id
                    )

                    db.session.add(event)
                    db.session.commit()

                    return f"""
                    <h2>Event Created Successfully ✅</h2>

                    <p>
                        Event:
                        <strong>{event.title}</strong>
                    </p>

                    <p>
                        Created by:
                        <strong>Event Coordinator</strong>
                    </p>

                    <p>
                        Status:
                        <strong>DRAFT</strong>
                    </p>

                    <p>
                        The event must be approved by
                        Faculty before students can register.
                    </p>

                    <p>
                        <a href="/dashboard">
                            Back to Dashboard
                        </a>
                    </p>
                    """

            except (ValueError, TypeError):

                message = (
                    "Please enter valid date, time "
                    "and capacity."
                )

    return render_template(
        "event_coordinator_create_event.html",
        club=club,
        message=message
    )
@main.route("/faculty/events/<int:event_id>/registrations")
@login_required
def faculty_event_registrations(event_id):

    from app.models import Event, EventRegistration, Student, User

    # Only Faculty can see registrations
    if current_user.role != "FACULTY":
        return "Only faculty can view registrations.", 403

    # Find event
    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Get all registered students
    registrations = (
        EventRegistration.query
        .filter_by(
            event_id=event.id,
            status="REGISTERED"
        )
        .all()
    )

    registered_students = []

    for registration in registrations:

        student = db.session.get(
            Student,
            registration.student_id
        )

        if not student:
            continue

        user = db.session.get(
            User,
            student.user_id
        )

        registered_students.append({
            "name": user.name if user else "Unknown",
            "email": user.email if user else "Unknown",
            "ra_number": student.ra_number,
            "registration_id": registration.id
        })

    return render_template(
        "faculty_event_registrations.html",
        event=event,
        registered_students=registered_students
    )
@main.route("/admin/clubs")
@login_required
def club_management():

    from app.models import Club, User

    # Only Super Admin and Admin can manage clubs
    if current_user.role not in ["SUPER_ADMIN", "ADMIN"]:
        return "403 Forbidden: You cannot manage clubs.", 403

    clubs = Club.query.order_by(Club.created_at.desc()).all()

    club_data = []

    for club in clubs:

        club_admin = None
        faculty_coordinator = None

        if club.club_admin_id:
            club_admin = db.session.get(User, club.club_admin_id)

        if club.faculty_coordinator_id:
            faculty_coordinator = db.session.get(
                User,
                club.faculty_coordinator_id
            )

        club_data.append({
            "club": club,
            "club_admin": club_admin,
            "faculty_coordinator": faculty_coordinator
        })

    return render_template(
        "club_management.html",
        club_data=club_data
    )

@main.route("/admin/clubs/create", methods=["GET", "POST"])
@login_required
def create_club():
    from app.models import Club, User

    # Only Super Admin and Admin can create clubs
    if current_user.role not in ["SUPER_ADMIN", "ADMIN"]:
        return "403 Forbidden: You cannot create clubs.", 403

    # Get users who can be assigned
    club_admins = User.query.filter_by(role="CLUB_ADMIN").all()
    faculty_coordinators = User.query.filter_by(role="FACULTY").all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        club_admin_id = request.form.get("club_admin_id")
        faculty_coordinator_id = request.form.get("faculty_coordinator_id")

        # Basic validation
        if not name:
            return "Club name is required.", 400

        # Prevent duplicate club names
        existing_club = Club.query.filter_by(name=name).first()
        if existing_club:
            return "A club with this name already exists.", 400

        # Create club
        club = Club(
            name=name,
            description=description,
            club_admin_id=int(club_admin_id) if club_admin_id else None,
            faculty_coordinator_id=int(faculty_coordinator_id)
            if faculty_coordinator_id else None,
            is_active=True
        )

        db.session.add(club)
        db.session.commit()

        return redirect("/admin/clubs")

    return render_template(
        "club_create.html",
        club_admins=club_admins,
        faculty_coordinators=faculty_coordinators
    )
@main.route("/admin/clubs/<int:club_id>/edit", methods=["GET", "POST"])
@login_required
def edit_club(club_id):
    from app.models import Club, User

    # Only Super Admin and Admin can edit clubs
    if current_user.role not in ["SUPER_ADMIN", "ADMIN"]:
        return "403 Forbidden: You cannot edit clubs.", 403

    club = db.session.get(Club, club_id)

    if not club:
        return "Club not found.", 404

    club_admins = User.query.filter_by(role="CLUB_ADMIN").all()
    faculty_coordinators = User.query.filter_by(role="FACULTY").all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        club_admin_id = request.form.get("club_admin_id")
        faculty_coordinator_id = request.form.get("faculty_coordinator_id")

        if not name:
            return "Club name is required.", 400

        # Check duplicate name, excluding current club
        existing_club = Club.query.filter(
            Club.name == name,
            Club.id != club_id
        ).first()

        if existing_club:
            return "Another club with this name already exists.", 400

        club.name = name
        club.description = description
        club.club_admin_id = int(club_admin_id) if club_admin_id else None
        club.faculty_coordinator_id = (
            int(faculty_coordinator_id)
            if faculty_coordinator_id
            else None
        )

        db.session.commit()

        return redirect("/admin/clubs")

    return render_template(
        "club_edit.html",
        club=club,
        club_admins=club_admins,
        faculty_coordinators=faculty_coordinators
    )
@main.route("/admin/clubs/<int:club_id>/toggle-status", methods=["POST"])
@login_required
def toggle_club_status(club_id):
    from app.models import Club

    # Only Super Admin and Admin can archive/activate clubs
    if current_user.role not in ["SUPER_ADMIN", "ADMIN"]:
        return "403 Forbidden: You cannot change club status.", 403

    club = db.session.get(Club, club_id)

    if not club:
        return "Club not found.", 404

    # Toggle ACTIVE <-> ARCHIVED
    club.is_active = not club.is_active

    db.session.commit()

    return redirect("/admin/clubs")
@main.route("/club-admin/test-member-permission/<int:club_id>")
@login_required
def test_member_permission(club_id):

    from app.permissions import has_permission

    if not has_permission("manage_event", club_id):
        return "❌ Permission DENIED: Member cannot manage events.", 403

    return "✅ Permission ALLOWED: Member can manage events."
# ==================================================

# STUDENT - MANAGE EVENTS
# ==================================================

@main.route("/student/manage-events")
@login_required
def student_manage_events():

    from app.models import Club, Event
    from app.permissions import has_permission

    # Current demo club
    club = Club.query.get(1)

    if not club:
        return "Club not found.", 404

    # Student must have at least one event-related permission
    can_manage_event = has_permission(
        "manage_event",
        club.id
    )

    can_manage_venue = has_permission(
        "manage_venue",
        club.id
    )

    can_manage_capacity = has_permission(
        "manage_capacity",
        club.id
    )

    can_submit_event = has_permission(
        "submit_event",
        club.id
    )

    # Student must have at least one permission
    if not (
        can_manage_event
        or can_manage_venue
        or can_manage_capacity
        or can_submit_event
    ):
        return (
            "403 Forbidden: You do not have event management permission.",
            403
        )

    events = Event.query.filter_by(
        club_id=club.id
    ).order_by(
        Event.event_date.asc()
    ).all()

    return render_template(
        "student_manage_events.html",
        club=club,
        events=events,
        can_manage_event=can_manage_event,
        can_manage_venue=can_manage_venue,
        can_manage_capacity=can_manage_capacity,
        can_submit_event=can_submit_event
    )
# ==================================================
# STUDENT - EDIT EVENT
# ==================================================

@main.route(
    "/student/manage-events/<int:event_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def student_edit_event(event_id):

    from app.models import Event
    from app.permissions import has_permission

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Check ONLY manage_event permission
    if not has_permission(
        "manage_event",
        event.club_id
    ):
        return (
            "403 Forbidden: You do not have permission to edit this event.",
            403
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not title:
            return "Event title is required.", 400

        event.title = title
        event.description = description

        db.session.commit()

        return redirect(
            "/student/manage-events"
        )

    return render_template(
        "student_edit_event.html",
        event=event
    )
# ==================================================
# STUDENT - MANAGE VENUE
# ==================================================

@main.route(
    "/student/manage-events/<int:event_id>/venue",
    methods=["POST"]
)
@login_required
def student_manage_venue(event_id):

    from app.models import Event
    from app.permissions import has_permission

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Check ONLY manage_venue permission
    if not has_permission(
        "manage_venue",
        event.club_id
    ):
        return (
            "403 Forbidden: You do not have permission to manage the venue.",
            403
        )

    venue = request.form.get(
        "venue",
        ""
    ).strip()

    if not venue:
        return "Venue is required.", 400

    event.venue = venue

    db.session.commit()

    return redirect(
        "/student/manage-events"
    )
# ==================================================
# STUDENT - MANAGE CAPACITY
# ==================================================

@main.route(
    "/student/manage-events/<int:event_id>/capacity",
    methods=["POST"]
)
@login_required
def student_manage_capacity(event_id):

    from app.models import Event
    from app.permissions import has_permission

    event = db.session.get(Event, event_id)

    if not event:
        return "Event not found.", 404

    # Check ONLY manage_capacity permission
    if not has_permission(
        "manage_capacity",
        event.club_id
    ):
        return (
            "403 Forbidden: You do not have permission to manage capacity.",
            403
        )

    capacity_value = request.form.get(
        "capacity",
        ""
    ).strip()

    try:
        capacity = int(capacity_value)
    except ValueError:
        return "Capacity must be a number.", 400

    if capacity <= 0:
        return "Capacity must be greater than zero.", 400

    event.capacity = capacity

    db.session.commit()

    return redirect(
        "/student/manage-events"
    )

@main.route("/faculty/notifications", methods=["GET"])
@login_required
def faculty_notifications():

    from app.models import Notification

    if current_user.role != "FACULTY":
        return "Only faculty can access notifications.", 403

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return render_template(
        "faculty_notifications.html",
        notifications=notifications
    )