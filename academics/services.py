"""
Academic operations service layer.

Provides atomic, testable business workflows:
- Scheme cloning and duplication
- Cohort semester progression and graduation transitions
- Automated course offering generation
- Bulk student enrollment engine
"""

from django.db import transaction
from django.core.exceptions import ValidationError

from academics.models import Scheme, Semester, Course, Batch, StudentProfile
from enrollment.models import CourseOffering, StudentCourseEnrollment


class AcademicWorkflowService:
    """Service providing core academic lifecycle operations."""

    @classmethod
    @transaction.atomic
    def clone_scheme(cls, source_scheme_id, new_code, new_name, effective_year):
        """
        Clones an existing curriculum scheme into a new regulation scheme,
        duplicating all semesters and child courses.
        """
        source = Scheme.objects.prefetch_related("semesters__courses").get(pk=source_scheme_id)

        # Create new Scheme
        cloned_scheme = Scheme.objects.create(
            program=source.program,
            code=new_code,
            name=new_name,
            effective_year=effective_year,
            total_credits_required=source.total_credits_required,
            is_active=True,
        )

        # Duplicate semesters & courses
        for sem in source.semesters.all():
            new_sem = Semester.objects.create(
                scheme=cloned_scheme,
                semester_number=sem.semester_number,
                semester_type=sem.semester_type,
            )

            courses_to_create = [
                Course(
                    semester=new_sem,
                    code=c.code,
                    title=c.title,
                    course_type=c.course_type,
                    credits=c.credits,
                    lecture_hours=c.lecture_hours,
                    tutorial_hours=c.tutorial_hours,
                    practical_hours=c.practical_hours,
                    syllabus_summary=c.syllabus_summary,
                )
                for c in sem.courses.all()
            ]
            Course.objects.bulk_create(courses_to_create)

        return cloned_scheme

    @classmethod
    @transaction.atomic
    def promote_batch(cls, batch_id):
        """
        Promotes a student batch to the next academic semester.
        If the cohort has reached the final semester, transitions the batch
        and its active students to GRADUATED.
        """
        batch = Batch.objects.select_related("program").get(pk=batch_id)

        if batch.is_graduated:
            raise ValidationError(f"Batch '{batch.name}' is already graduated.")

        max_semesters = batch.program.total_semesters

        if batch.current_semester < max_semesters:
            batch.current_semester += 1
            batch.save(update_fields=["current_semester"])
            return {
                "status": "PROMOTED",
                "new_semester": batch.current_semester,
                "message": f"Batch '{batch.name}' successfully promoted to Semester {batch.current_semester}.",
            }
        else:
            batch.is_graduated = True
            batch.save(update_fields=["is_graduated"])

            # Transition active students
            StudentProfile.objects.filter(
                batch=batch,
                status=StudentProfile.StudentStatus.ACTIVE,
            ).update(status=StudentProfile.StudentStatus.GRADUATED)

            return {
                "status": "GRADUATED",
                "new_semester": batch.current_semester,
                "message": f"Batch '{batch.name}' has completed all {max_semesters} semesters and graduated successfully.",
            }

    @classmethod
    @transaction.atomic
    def generate_course_offerings_for_batch(cls, batch_id, academic_year, term, section="A", default_faculty_map=None):
        """
        Pulls all curriculum courses configured for the batch's current active semester
        and generates live CourseOffering instances.
        """
        batch = Batch.objects.select_related("scheme").get(pk=batch_id)
        current_sem_number = batch.current_semester

        # Find semester definition in batch's scheme
        semester = Semester.objects.prefetch_related("courses").filter(
            scheme=batch.scheme,
            semester_number=current_sem_number,
        ).first()

        if not semester:
            raise ValidationError(
                f"No Semester {current_sem_number} defined under scheme '{batch.scheme.code}'."
            )

        offerings_created = []
        default_faculty_map = default_faculty_map or {}

        for course in semester.courses.all():
            faculty = default_faculty_map.get(course.code) or default_faculty_map.get(str(course.id))
            offering, created = CourseOffering.objects.get_or_create(
                course=course,
                batch=batch,
                academic_year=academic_year,
                term=term,
                section=section,
                defaults={
                    "faculty": faculty,
                    "is_active": True,
                },
            )
            offerings_created.append(offering)

        return offerings_created

    @classmethod
    @transaction.atomic
    def bulk_enroll_batch_students(cls, batch_id, academic_year, term, section="A"):
        """
        Enrolls all ACTIVE students belonging to a batch into all active course offerings
        for that batch, academic year, term, and section.
        High-performance bulk insertion.
        """
        batch = Batch.objects.get(pk=batch_id)

        # Retrieve offerings
        offerings = list(CourseOffering.objects.filter(
            batch=batch,
            academic_year=academic_year,
            term=term,
            section=section,
            is_active=True,
        ))

        if not offerings:
            raise ValidationError("No active course offerings found for this batch and academic term.")

        # Active students in batch
        active_students = list(StudentProfile.objects.filter(
            batch=batch,
            status=StudentProfile.StudentStatus.ACTIVE,
        ))

        if not active_students:
            return 0

        # Existing enrollments check to avoid duplicates
        existing_keys = set(
            StudentCourseEnrollment.objects.filter(
                student__in=active_students,
                course_offering__in=offerings,
            ).values_list("student_id", "course_offering_id")
        )

        enrollments_to_create = []
        for student in active_students:
            for offering in offerings:
                if (student.id, offering.id) not in existing_keys:
                    enrollments_to_create.append(
                        StudentCourseEnrollment(
                            student=student,
                            course_offering=offering,
                            status=StudentCourseEnrollment.EnrollmentStatus.ENROLLED,
                        )
                    )

        if enrollments_to_create:
            StudentCourseEnrollment.objects.bulk_create(enrollments_to_create, ignore_conflicts=True)

        return len(enrollments_to_create)

    @classmethod
    @transaction.atomic
    def bulk_import_students_from_csv(cls, batch_id, csv_file_or_content):
        """
        Parses CSV input and registers new students with associated User accounts into the specified batch.
        Expected CSV headers:
        register_number, roll_number, first_name, last_name, email, blood_group, emergency_contact
        """
        import csv
        import io
        from accounts.models import User

        batch = Batch.objects.get(pk=batch_id)

        if hasattr(csv_file_or_content, "read"):
            raw = csv_file_or_content.read()
            if isinstance(raw, bytes):
                decoded = raw.decode("utf-8-sig", errors="replace")
            else:
                decoded = str(raw)
        elif isinstance(csv_file_or_content, bytes):
            decoded = csv_file_or_content.decode("utf-8-sig", errors="replace")
        else:
            decoded = str(csv_file_or_content)

        reader = csv.DictReader(io.StringIO(decoded))

        imported_students = []
        skipped_records = []

        existing_usns = set(StudentProfile.objects.values_list("register_number", flat=True))
        existing_usernames = set(User.objects.values_list("username", flat=True))

        for row_num, row in enumerate(reader, start=2):
            # Clean keys (strip whitespace and lower case)
            clean_row = {k.strip().lower() if k else "": v.strip() if v else "" for k, v in row.items()}

            reg_no = clean_row.get("register_number") or clean_row.get("usn") or clean_row.get("reg_no")
            if not reg_no:
                skipped_records.append(f"Row {row_num}: Missing register_number / USN.")
                continue

            if reg_no in existing_usns:
                skipped_records.append(f"Row {row_num}: USN '{reg_no}' already exists in database.")
                continue

            first_name = clean_row.get("first_name") or "Student"
            last_name = clean_row.get("last_name") or ""
            email = clean_row.get("email") or f"{reg_no.lower()}@rvce.edu.in"
            roll_no = clean_row.get("roll_number") or clean_row.get("roll_no") or ""
            blood_group = clean_row.get("blood_group") or "O+"
            emergency = clean_row.get("emergency_contact") or ""

            # Ensure unique username
            base_username = reg_no.lower().replace("/", "_").replace("-", "_")
            username = base_username
            counter = 1
            while username in existing_usernames:
                username = f"{base_username}_{counter}"
                counter += 1
            existing_usernames.add(username)

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.STUDENT,
                password="pass123",
            )

            profile = StudentProfile.objects.create(
                user=user,
                batch=batch,
                register_number=reg_no,
                roll_number=roll_no,
                blood_group=blood_group,
                emergency_contact=emergency,
                status=StudentProfile.StudentStatus.ACTIVE,
            )
            existing_usns.add(reg_no)
            imported_students.append(profile)

        return {
            "imported_count": len(imported_students),
            "skipped_count": len(skipped_records),
            "skipped_records": skipped_records,
            "message": f"Successfully registered {len(imported_students)} students into '{batch.name}'. Skipped {len(skipped_records)} records.",
        }

    @classmethod
    def generate_student_transcript(cls, student_id):
        """
        Generates official academic transcript data for a student, calculating:
        - Semester-wise breakdown of courses, credits, letter grades, and grade points
        - Semester Grade Point Average (SGPA) for each completed/evaluated term
        - Cumulative Grade Point Average (CGPA) across entire academic tenure
        - Total credits registered vs. total credits successfully earned
        """
        from decimal import Decimal
        from academics.models import StudentProfile
        from enrollment.models import StudentCourseEnrollment

        student = StudentProfile.objects.select_related(
            "user",
            "batch__program__department__college",
            "batch__scheme",
        ).get(pk=student_id)

        enrollments = (
            StudentCourseEnrollment.objects.filter(student=student)
            .select_related(
                "course_offering__course__semester",
                "course_offering__course",
                "course_offering__faculty__user",
            )
            .prefetch_related("marks__component")
            .order_by("course_offering__academic_year", "course_offering__term", "course_offering__course__code")
        )

        grade_points_map = {
            "O": Decimal("10.00"),
            "S": Decimal("10.00"),
            "A+": Decimal("10.00"),
            "A": Decimal("9.00"),
            "B+": Decimal("8.00"),
            "B": Decimal("7.00"),
            "C+": Decimal("6.50"),
            "C": Decimal("6.00"),
            "D": Decimal("5.00"),
            "P": Decimal("4.00"),
            "F": Decimal("0.00"),
        }

        semesters_dict = {}
        for enr in enrollments:
            offering = enr.course_offering
            course = offering.course
            sem_num = course.semester.semester_number if course.semester else 1
            sem_label = f"Semester {sem_num} ({offering.academic_year} {offering.term})"
            key = (sem_num, offering.academic_year, offering.term)

            if key not in semesters_dict:
                semesters_dict[key] = {
                    "semester_number": sem_num,
                    "academic_year": offering.academic_year,
                    "term": offering.term,
                    "label": sem_label,
                    "courses": [],
                    "credits_registered": Decimal("0.00"),
                    "credits_earned": Decimal("0.00"),
                    "total_grade_points": Decimal("0.00"),
                    "graded_credits": Decimal("0.00"),
                    "sgpa": None,
                }

            grade = (enr.grade or "").strip().upper()
            gp = grade_points_map.get(grade)

            course_credits = Decimal(str(course.credits))
            semesters_dict[key]["credits_registered"] += course_credits

            earned = Decimal("0.00")
            if grade and grade != "F":
                earned = course_credits
                semesters_dict[key]["credits_earned"] += earned

            credit_pts = None
            if gp is not None:
                credit_pts = course_credits * gp
                semesters_dict[key]["total_grade_points"] += credit_pts
                semesters_dict[key]["graded_credits"] += course_credits

            semesters_dict[key]["courses"].append({
                "enrollment": enr,
                "course": course,
                "credits": course_credits,
                "grade": grade or "PENDING",
                "grade_point": gp,
                "credit_points": credit_pts,
                "attendance_percentage": enr.attendance_percentage,
                "status": enr.status,
            })

        sorted_semesters = sorted(semesters_dict.values(), key=lambda x: (x["semester_number"], x["academic_year"]))

        cum_graded_credits = Decimal("0.00")
        cum_grade_points = Decimal("0.00")
        total_credits_registered = Decimal("0.00")
        total_credits_earned = Decimal("0.00")

        for sem in sorted_semesters:
            if sem["graded_credits"] > Decimal("0.00"):
                sem["sgpa"] = round(sem["total_grade_points"] / sem["graded_credits"], 2)
                cum_graded_credits += sem["graded_credits"]
                cum_grade_points += sem["total_grade_points"]
            total_credits_registered += sem["credits_registered"]
            total_credits_earned += sem["credits_earned"]

        cgpa = None
        if cum_graded_credits > Decimal("0.00"):
            cgpa = round(cum_grade_points / cum_graded_credits, 2)

        return {
            "student": student,
            "semesters": sorted_semesters,
            "total_credits_registered": total_credits_registered,
            "total_credits_earned": total_credits_earned,
            "cgpa": cgpa,
            "is_graduated": student.batch.is_graduated,
        }


