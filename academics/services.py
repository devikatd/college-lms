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
