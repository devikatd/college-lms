"""
Management command to seed realistic academic demo data into the College LMS.

Populates:
- 1 College
- 3 Departments (CSE, ISE, ECE)
- 3 Degree Programs (B.Tech CSE, M.Tech Data Science, B.Tech ECE)
- 2 Curriculum Schemes (2024 CBCS Regulation, 2022 Autonomous Scheme)
- 8 Semesters with 16 comprehensive Courses (L-T-P, credits, syllabi)
- 2 Batches (2023-2027 CSE, 2024-2028 CSE)
- 1 Department Admin user (dept_admin_cs / pass123)
- 3 Faculty users with FacultyProfiles (dr_alan, prof_grace, dr_ada / pass123)
- 4 Student users with StudentProfiles (student_rahul, student_priya, student_arjun, student_ananya / pass123)
- 4 Course Offerings with Student Course Enrollments
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from academics.models import (
    College,
    Department,
    Program,
    Scheme,
    Semester,
    Course,
    Batch,
    FacultyProfile,
    StudentProfile,
)
from enrollment.models import (
    CourseOffering,
    StudentCourseEnrollment,
    AttendanceSession,
    AttendanceRecord,
    AssessmentComponent,
    StudentMark,
    TimetableEntry,
    CourseMaterial,
)
from portal.models import AcademicNotice



class Command(BaseCommand):
    help = "Seeds comprehensive academic hierarchy and user profiles for College LMS."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Beginning academic demo data seeding..."))

        # ── 1. College ────────────────────────────────────────────────────────
        college, _ = College.objects.get_or_create(
            code="RVCE",
            defaults={
                "name": "R.V. College of Engineering",
                "established_year": 1963,
                "address": "Mysore Road, RV Vidyaniketan, Bengaluru, Karnataka 560059",
                "website": "https://www.rvce.edu.in",
            },
        )
        self.stdout.write(f"  [OK] College: {college.name}")

        # ── 2. Departments ───────────────────────────────────────────────────
        cse_dept, _ = Department.objects.get_or_create(
            college=college,
            code="CSE",
            defaults={
                "name": "Department of Computer Science & Engineering",
                "description": "Leading department dedicated to computing theory, systems architecture, and intelligent software systems.",
            },
        )
        ise_dept, _ = Department.objects.get_or_create(
            college=college,
            code="ISE",
            defaults={
                "name": "Department of Information Science & Engineering",
                "description": "Excellence in data analytics, cloud computing, cybersecurity, and information management.",
            },
        )
        ece_dept, _ = Department.objects.get_or_create(
            college=college,
            code="ECE",
            defaults={
                "name": "Department of Electronics & Communication Engineering",
                "description": "Pioneering VLSI design, embedded systems, signal processing, and RF communications.",
            },
        )
        self.stdout.write(f"  [OK] 3 Departments created/verified.")

        # ── 3. Programs ──────────────────────────────────────────────────────
        btech_cs, _ = Program.objects.get_or_create(
            department=cse_dept,
            code="BTECH-CS",
            defaults={
                "name": "Bachelor of Technology in Computer Science & Engineering",
                "degree_type": Program.DegreeType.UG,
                "duration_years": 4,
                "total_semesters": 8,
            },
        )
        mtech_ds, _ = Program.objects.get_or_create(
            department=cse_dept,
            code="MTECH-DS",
            defaults={
                "name": "Master of Technology in Data Science",
                "degree_type": Program.DegreeType.PG,
                "duration_years": 2,
                "total_semesters": 4,
            },
        )
        btech_ec, _ = Program.objects.get_or_create(
            department=ece_dept,
            code="BTECH-EC",
            defaults={
                "name": "Bachelor of Technology in Electronics & Communication",
                "degree_type": Program.DegreeType.UG,
                "duration_years": 4,
                "total_semesters": 8,
            },
        )
        self.stdout.write(f"  [OK] 3 Programs created/verified.")

        # ── 4. Curriculum Schemes ────────────────────────────────────────────
        scheme_2024, _ = Scheme.objects.get_or_create(
            program=btech_cs,
            code="SCH2024-CS",
            defaults={
                "name": "2024 Outcome Based CBCS Curriculum",
                "effective_year": 2024,
                "total_credits_required": Decimal("160.00"),
                "is_active": True,
            },
        )
        scheme_2022, _ = Scheme.objects.get_or_create(
            program=btech_cs,
            code="SCH2022-CS",
            defaults={
                "name": "2022 Autonomous Regulation Scheme",
                "effective_year": 2022,
                "total_credits_required": Decimal("160.00"),
                "is_active": True,
            },
        )
        self.stdout.write(f"  [OK] 2 Curriculum Schemes created/verified.")

        # ── 5. Semesters & Courses (Scheme 2024) ──────────────────────────────
        semesters_data = [
            (1, Semester.SemesterType.ODD),
            (2, Semester.SemesterType.EVEN),
            (3, Semester.SemesterType.ODD),
            (4, Semester.SemesterType.EVEN),
            (5, Semester.SemesterType.ODD),
            (6, Semester.SemesterType.EVEN),
            (7, Semester.SemesterType.ODD),
            (8, Semester.SemesterType.EVEN),
        ]

        sem_map = {}
        for sem_no, sem_type in semesters_data:
            s, _ = Semester.objects.get_or_create(
                scheme=scheme_2024,
                semester_number=sem_no,
                defaults={"semester_type": sem_type},
            )
            sem_map[sem_no] = s

        courses_data = [
            # Sem 1
            (1, "MAT101", "Calculus and Linear Algebra", Course.CourseType.CORE, Decimal("4.00"), 3, 1, 0, "Matrices, eigenvalues, single and multivariate calculus, vector spaces."),
            (1, "CS101", "Problem Solving with Python", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "Variables, control structures, lists, functions, file IO, and OOP basics in Python."),
            (1, "PHY101", "Engineering Physics & Lab", Course.CourseType.LAB, Decimal("3.00"), 2, 0, 2, "Quantum mechanics, laser optics, and semiconductor physics."),
            # Sem 2
            (2, "CS102", "Object-Oriented Programming with C++", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "Pointers, classes, inheritance, polymorphism, templates, and STL containers."),
            (2, "MAT201", "Differential Equations and Complex Analysis", Course.CourseType.CORE, Decimal("4.00"), 3, 1, 0, "Ordinary differential equations, Fourier transforms, Laplace transforms."),
            # Sem 3
            (3, "CS301", "Data Structures and Algorithms", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "Arrays, linked lists, trees, graphs, sorting, searching, and algorithmic complexity."),
            (3, "CS302", "Digital Logic and Computer Organization", Course.CourseType.CORE, Decimal("4.00"), 3, 1, 0, "Boolean algebra, combinational circuits, sequential circuits, CPU architecture, memory hierarchy."),
            (3, "CS303", "Discrete Mathematics", Course.CourseType.CORE, Decimal("3.00"), 3, 0, 0, "Propositional logic, set theory, graph theory, combinatorics, and recurrence relations."),
            # Sem 4
            (4, "CS401", "Design and Analysis of Algorithms", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "Greedy algorithms, divide and conquer, dynamic programming, backtracking, NP-completeness."),
            (4, "CS402", "Database Management Systems", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "ER modeling, relational algebra, SQL, normalization, transactions, ACID, indexing, and NoSQL."),
            (4, "CS403", "Operating Systems & System Programming", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "Processes, threads, CPU scheduling, synchronization, deadlocks, virtual memory."),
            # Sem 5
            (5, "CS501", "Computer Networks", Course.CourseType.CORE, Decimal("4.00"), 3, 0, 2, "OSI/TCP-IP models, packet routing, transport layer congestion control, DNS, HTTP, socket programming."),
            (5, "CS502", "Theory of Computation & Automata", Course.CourseType.CORE, Decimal("3.00"), 3, 1, 0, "DFA, NFA, regular expressions, context-free grammars, pushdown automata, Turing machines."),
            (5, "CS503", "Machine Learning Foundations", Course.CourseType.ELECTIVE, Decimal("3.00"), 3, 0, 0, "Supervised learning, linear regression, SVM, decision trees, neural networks, cross-validation."),
            # Sem 6
            (6, "CS601", "Software Engineering & DevOps", Course.CourseType.CORE, Decimal("3.00"), 2, 0, 2, "Agile methodology, CI/CD pipelines, Docker containerization, Git workflows, testing."),
            (6, "CS602", "Cloud Computing & Distributed Systems", Course.CourseType.ELECTIVE, Decimal("3.00"), 3, 0, 0, "Virtualization, AWS/GCP architecture, microservices, consensus protocols, Kafka."),
        ]

        course_map = {}
        for sem_no, code, title, c_type, credits, l, t, p, syllabus in courses_data:
            c, _ = Course.objects.get_or_create(
                semester=sem_map[sem_no],
                code=code,
                defaults={
                    "title": title,
                    "course_type": c_type,
                    "credits": credits,
                    "lecture_hours": l,
                    "tutorial_hours": t,
                    "practical_hours": p,
                    "syllabus_summary": syllabus,
                },
            )
            course_map[code] = c

        self.stdout.write(f"  [OK] 8 Semesters and 16 Courses created/verified.")

        # ── 6. Batches ───────────────────────────────────────────────────────
        batch_23, _ = Batch.objects.get_or_create(
            program=btech_cs,
            admission_year=2023,
            name="2023-2027 CSE Batch A",
            defaults={
                "scheme": scheme_2022,
                "graduation_year": 2027,
                "current_semester": 3,
                "is_graduated": False,
            },
        )

        batch_24, _ = Batch.objects.get_or_create(
            program=btech_cs,
            admission_year=2024,
            name="2024-2028 CSE Batch A",
            defaults={
                "scheme": scheme_2024,
                "graduation_year": 2028,
                "current_semester": 1,
                "is_graduated": False,
            },
        )
        self.stdout.write(f"  [OK] 2 Student Batches created/verified.")

        # ── 7. Department Admin User ─────────────────────────────────────────
        dept_admin_user, created = User.objects.get_or_create(
            username="dept_admin_cs",
            defaults={
                "email": "hod.cse@rvce.edu.in",
                "first_name": "Kavitha",
                "last_name": "Narayanan",
                "role": User.Role.DEPT_ADMIN,
                "assigned_department": cse_dept,
                "is_staff": True,
            },
        )
        if created:
            dept_admin_user.set_password("pass123")
            dept_admin_user.save()
        else:
            dept_admin_user.assigned_department = cse_dept
            dept_admin_user.save()

        # ── 8. Faculty Users & Profiles ──────────────────────────────────────
        faculty_roster = [
            ("dr_alan", "Alan", "Turing", "alan.turing@rvce.edu.in", "EMP-CS-101", "Professor & HOD", "Ph.D. in Computer Science (Cambridge)"),
            ("prof_grace", "Grace", "Hopper", "grace.hopper@rvce.edu.in", "EMP-CS-102", "Associate Professor", "Ph.D. in Mathematics (Yale)"),
            ("dr_ada", "Ada", "Lovelace", "ada.lovelace@rvce.edu.in", "EMP-CS-103", "Assistant Professor", "M.Tech, Ph.D. in Artificial Intelligence (London)"),
        ]

        faculty_profile_map = {}
        for username, first, last, email, emp_id, designation, qual in faculty_roster:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "role": User.Role.FACULTY,
                    "is_staff": True,
                },
            )
            if created:
                u.set_password("pass123")
                u.save()

            fp, _ = FacultyProfile.objects.get_or_create(
                user=u,
                defaults={
                    "department": cse_dept,
                    "employee_id": emp_id,
                    "designation": designation,
                    "qualification": qual,
                    "cabin_location": "CS Dept Room 204",
                },
            )
            faculty_profile_map[username] = fp

        self.stdout.write(f"  [OK] 1 Dept Admin and 3 Faculty users created/verified.")

        # ── 9. Student Users & Profiles ──────────────────────────────────────
        students_roster = [
            ("student_rahul", "Rahul", "Sharma", "rahul.sharma@rvce.edu.in", "1RV24CS001", "CS-01", batch_24),
            ("student_priya", "Priya", "Menon", "priya.menon@rvce.edu.in", "1RV24CS002", "CS-02", batch_24),
            ("student_arjun", "Arjun", "Verma", "arjun.verma@rvce.edu.in", "1RV24CS003", "CS-03", batch_24),
            ("student_ananya", "Ananya", "Rao", "ananya.rao@rvce.edu.in", "1RV23CS015", "CS-15", batch_23),
        ]

        student_profile_map = {}
        for username, first, last, email, reg_no, roll_no, batch in students_roster:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "role": User.Role.STUDENT,
                },
            )
            if created:
                u.set_password("pass123")
                u.save()

            sp, _ = StudentProfile.objects.get_or_create(
                user=u,
                defaults={
                    "batch": batch,
                    "register_number": reg_no,
                    "roll_number": roll_no,
                    "status": StudentProfile.StudentStatus.ACTIVE,
                    "blood_group": "B+",
                },
            )
            student_profile_map[username] = sp

        self.stdout.write(f"  [OK] 4 Student profiles created/verified.")

        # ── 10. Course Offerings & Enrollments ────────────────────────────────
        # Offerings for 2024-2028 Batch A (Sem 1 courses)
        offerings_data = [
            (course_map["CS101"], batch_24, faculty_profile_map["dr_alan"], "2024-2025", CourseOffering.Term.ODD, "A"),
            (course_map["MAT101"], batch_24, faculty_profile_map["prof_grace"], "2024-2025", CourseOffering.Term.ODD, "A"),
            (course_map["PHY101"], batch_24, faculty_profile_map["dr_ada"], "2024-2025", CourseOffering.Term.ODD, "A"),
        ]

        for course, batch, faculty, ac_year, term, sec in offerings_data:
            offering, _ = CourseOffering.objects.get_or_create(
                course=course,
                batch=batch,
                academic_year=ac_year,
                term=term,
                section=sec,
                defaults={"faculty": faculty, "is_active": True},
            )

            # Enroll Sem 1 students with varied realistic attendance profiles and grades
            enroll_profiles = [
                ("student_rahul", Decimal("94.50"), "A+"),
                ("student_priya", Decimal("98.00"), "O"),
                ("student_arjun", Decimal("76.50"), "B+"),  # Warning threshold
                ("student_ananya", Decimal("62.50"), "B"), # Critical Shortage (<75%)
            ]
            for uname, att_pct, grade in enroll_profiles:
                if uname in student_profile_map:
                    sp = student_profile_map[uname]
                    enr, _ = StudentCourseEnrollment.objects.get_or_create(
                        student=sp,
                        course_offering=offering,
                        defaults={
                            "status": StudentCourseEnrollment.EnrollmentStatus.ENROLLED,
                            "attendance_percentage": att_pct,
                            "grade": grade,
                        },
                    )
                    enr.attendance_percentage = att_pct
                    enr.grade = grade
                    enr.save()


        # ── 11. Extensibility Seeds: Attendance Sessions & CIE Marks ─────────
        cs101_offering = CourseOffering.objects.filter(course=course_map["CS101"]).first()
        if cs101_offering:
            import datetime
            from datetime import time
            today = datetime.date.today()

            # Create an attendance session
            session, _ = AttendanceSession.objects.get_or_create(
                course_offering=cs101_offering,
                date=today,
                slot=1,
                defaults={"topic_covered": "Introduction to Python Data Structures & Algorithmic Complexity"},
            )

            # Record attendance for enrolled students
            for uname in ["student_rahul", "student_priya", "student_arjun"]:
                sp = student_profile_map[uname]
                AttendanceRecord.objects.get_or_create(
                    session=session,
                    student=sp,
                    defaults={"is_present": True, "remarks": "Present on time"},
                )

            # Create an assessment component (CIE Test 1)
            cie_test1, _ = AssessmentComponent.objects.get_or_create(
                course_offering=cs101_offering,
                name="Continuous Internal Evaluation Test 1 (CIE-1)",
                defaults={
                    "max_marks": Decimal("50.00"),
                    "weightage_percentage": Decimal("25.00"),
                    "conducted_date": today,
                },
            )

            # Enter student marks
            marks_dist = {
                "student_rahul": Decimal("46.50"),
                "student_priya": Decimal("48.00"),
                "student_arjun": Decimal("38.00"),
                "student_ananya": Decimal("28.50"),
            }
            for uname, score in marks_dist.items():
                if uname in student_profile_map:
                    sp = student_profile_map[uname]
                    enr = StudentCourseEnrollment.objects.filter(student=sp, course_offering=cs101_offering).first()
                    if enr:
                        StudentMark.objects.get_or_create(
                            component=cie_test1,
                            enrollment=enr,
                            defaults={"marks_obtained": score},
                        )

            # ── 12. Weekly Timetable Entries ──────────────────────────────────
            timetable_slots = [
                ("MON", 1, time(9, 0), time(10, 0), "LH-201"),
                ("WED", 2, time(10, 0), time(11, 0), "LH-201"),
                ("THU", 4, time(12, 15), time(13, 15), "LH-201"),
                ("FRI", 5, time(14, 0), time(16, 0), "CS-LAB-2"),
            ]
            for day, slot, start_t, end_t, room in timetable_slots:
                TimetableEntry.objects.get_or_create(
                    course_offering=cs101_offering,
                    day_of_week=day,
                    slot_number=slot,
                    defaults={
                        "start_time": start_t,
                        "end_time": end_t,
                        "classroom": room,
                    },
                )

            # ── 13. Digital Learning Materials ────────────────────────────────
            materials = [
                ("Course Syllabus & Academic Plan 2024-25", CourseMaterial.MaterialType.SYLLABUS, "Detailed 16-week lecture plan, textbook references, and grading rubrics.", "https://drive.google.com/lms/syllabus-cs101.pdf"),
                ("Unit 1: Python Memory Hierarchy & Pointers", CourseMaterial.MaterialType.LECTURE_NOTES, "Slides covering PyObject memory layouts, reference counts, garbage collection, and mutable vs immutable data types.", "https://drive.google.com/lms/unit1-notes.pdf"),
                ("Assignment 1: High-Performance Data Structures", CourseMaterial.MaterialType.ASSIGNMENT, "Problem set implementing doubly linked lists, ring buffers, and benchmark timing comparisons.", "https://drive.google.com/lms/assignment1.pdf"),
                ("Python 3.12 Standard Library Official Documentation", CourseMaterial.MaterialType.REFERENCE, "Comprehensive language reference manual and standard library API guides.", "https://docs.python.org/3/"),
            ]
            for title, m_type, desc, url in materials:
                CourseMaterial.objects.get_or_create(
                    course_offering=cs101_offering,
                    title=title,
                    defaults={
                        "material_type": m_type,
                        "description": desc,
                        "resource_url": url,
                    },
                )

            self.stdout.write(f"  [OK] Attendance sessions, CIE marks, Timetable, and Materials initialized.")

            # ── 14. Campus Notices & Institutional Circulars ──────────────────
            admin_user = User.objects.filter(role=User.Role.COLLEGE_ADMIN).first()
            dept_admin = User.objects.filter(username="dept_admin_cs").first()
            notices_seed = [
                (
                    "Annual Institutional Tech Symposium & Hackathon 2026",
                    "We are thrilled to announce the 2026 RVCE Tech Symposium! Students across all departments are invited to submit innovative engineering projects, capstone prototypes, and research posters. Registration opens next Monday.",
                    AcademicNotice.Category.EVENT,
                    AcademicNotice.Priority.IMPORTANT,
                    AcademicNotice.TargetRole.ALL,
                    None,
                    admin_user,
                    "https://www.rvce.edu.in/symposium-2026",
                ),
                (
                    "End-Semester Examination Time-Table & Hall Ticket Generation",
                    "The final examination schedule for Odd Semester 2024-2025 has been ratified by the Controller of Examinations. Students with minimum 75% attendance can download their hall tickets from the student portal starting Friday.",
                    AcademicNotice.Category.EXAM,
                    AcademicNotice.Priority.CRITICAL,
                    AcademicNotice.TargetRole.STUDENT,
                    None,
                    admin_user,
                    "https://www.rvce.edu.in/exams/timetable.pdf",
                ),
                (
                    "Department Curriculum Review Committee Meeting: 2026 Regulation",
                    "A mandatory meeting for all Computer Science & Engineering faculty members is scheduled for Wednesday at 3:00 PM in Seminar Hall 1 to review AI/ML curriculum integration.",
                    AcademicNotice.Category.CIRCULAR,
                    AcademicNotice.Priority.NORMAL,
                    AcademicNotice.TargetRole.FACULTY,
                    cse_dept,
                    dept_admin,
                    "",
                ),
                (
                    "Campus Wi-Fi Network Maintenance & Fiber Backbone Upgrade",
                    "IT Infrastructure services will be carrying out planned core switch maintenance on Saturday between 11:00 PM and 3:00 AM. Intermittent internet access may be experienced across campus hostels and labs.",
                    AcademicNotice.Category.URGENT,
                    AcademicNotice.Priority.IMPORTANT,
                    AcademicNotice.TargetRole.ALL,
                    None,
                    admin_user,
                    "",
                ),
            ]
            for title, content, cat, prio, target, dept_obj, pub, url in notices_seed:
                AcademicNotice.objects.get_or_create(
                    title=title,
                    defaults={
                        "content": content,
                        "category": cat,
                        "priority": prio,
                        "target_role": target,
                        "department": dept_obj,
                        "publisher": pub,
                        "attachment_url": url,
                        "is_active": True,
                    },
                )
            self.stdout.write(f"  [OK] 4 Institutional Academic Notices seeded.")


        self.stdout.write(self.style.SUCCESS("Demo academic data seeding completed successfully!"))
