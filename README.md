# College Learning Management System (LMS)

A modern, centralized, and role-based academic administration platform engineered in Python and Django. Designed to streamline academic data management, eliminate data duplication, ensure institutional data integrity, and provide tailored workflows for administrators, department heads, faculty members, and students.

---

## Table of Contents

- [Overview & Problem Statement](#overview--problem-statement)
- [Academic Hierarchy Architecture](#academic-hierarchy-architecture)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [System Capabilities & Features](#system-capabilities--features)
- [Zero-Cost Open Source Stack](#zero-cost-open-source-stack)
- [Quickstart & Local Installation](#quickstart--local-installation)
- [Pre-Seeded Demo Credentials](#pre-seeded-demo-credentials)
- [Automated Testing Suite](#automated-testing-suite)
- [Production Deployment](#production-deployment)

---

## Overview & Problem Statement

Colleges and autonomous universities manage a vast web of interrelated academic data: colleges, departments, degree programs, curriculum regulation schemes, semesters, syllabi, student cohorts/batches, enrollments, attendance, and evaluation records.

When maintained across disconnected spreadsheets or fragmented legacy tools, institutions suffer from:
- **Data Duplication:** Redundant records across department offices and central administration.
- **Update Anomalies:** Desynchronized syllabi, schemes, or student rosters.
- **Slow Record Retrieval:** Inability to locate student transcripts or course records rapidly.
- **Manual Overhead:** Labor-intensive student onboarding, attendance calculations, and cohort promotions.
- **Unauthorized Data Access:** Lack of fine-grained role boundaries.

This College LMS provides an authoritative centralized platform with relational integrity constraints, cascading validations, and role-specific portals.

---

## Academic Hierarchy Architecture

The system models higher-education academic structures strictly through a relational hierarchy:

```
[ College ] (Apex Entity)
    └── [ Departments ] (e.g., Computer Science & Engineering)
            ├── [ Degree Programs ] (e.g., B.Tech in CSE, M.Tech Data Science)
            │       │
            │       ├── [ Curriculum Schemes ] (e.g., 2024 CBCS Regulation)
            │       │       └── [ Semesters ] (Semesters 1 through 8)
            │       │               └── [ Courses ] (Title, L-T-P, Credits, Syllabi)
            │       │
            │       └── [ Student Batches / Cohorts ] (e.g., 2024–2028 CSE Section A)
            │               │
            │               ├── [ Enrolled Students ] (USN, Dossier, Profiles)
            │               │
            │               └── [ Live Course Offerings ] (Term, Academic Year, Section)
            │                       ├── Faculty Assignment
            │                       ├── Student Course Enrollments
            │                       ├── Attendance Sessions & Tracking
            │                       ├── Continuous Internal Evaluation (CIE) Marks
            │                       ├── Weekly Class Timetable Schedule
            │                       └── Digital Course Syllabi & Learning Materials
```

---

## Role-Based Access Control (RBAC)

The platform enforces strict role boundaries:

| Capability / Module | College Admin | Department Admin | Faculty Staff | Enrolled Student |
| :--- | :---: | :---: | :---: | :---: |
| **Institution-Wide Analytics** | Full Access | Scoped to Dept | Personal | Personal |
| **Department Management** | Full CRUD | View Only | View Only | — |
| **Degree Program Management** | Full CRUD | Dept CRUD | View Only | View Only |
| **Curriculum Schemes & Cloning** | Full CRUD | Dept CRUD | View Only | View Roadmap |
| **Courses & Syllabi** | Full CRUD | Dept CRUD | View Only | Enrolled Subjects |
| **Batch Promotion & Management** | Full Access | Dept Scoped | View Roster | Enrolled Cohort |
| **Bulk CSV Student Onboarding** | Full Access | Dept Scoped | — | — |
| **Attendance & CIE Marking** | Oversee | Oversee | Mark & Record | View Own Attendance |
| **Attendance Alerts (<75% Shortage)** | Institution-wide | Dept-scoped | Course-scoped | Personal Warning |
| **Official Transcript & Grade Card** | View All | Dept-scoped | Dept-scoped | View & Print Own |
| **Campus Notice Board** | Full Broadcast | Dept Broadcast | View Circulars | View Circulars |

---

## System Capabilities & Features

### 1. Interactive Academic CRUD Workstations
- Dedicated management workstations for Departments, Degree Programs, Curriculum Schemes, Courses, Batches, Student Dossiers, and Faculty Rosters.
- Cascading dynamic dropdowns (`College -> Department -> Program -> Scheme -> Semester -> Course`) powered by JSON APIs.

### 2. Scheme Cloning Engine
- Clone an entire multi-year curriculum scheme into a new academic regulation with a single action. Automatically duplicates child semesters and course syllabi.

### 3. Bulk CSV Student Onboarding
- Rapidly register an entire class cohort by uploading a `.csv` roster.
- Automatically provisions user accounts with secure default passwords and creates linked student academic dossiers.
- Provides downloadable pre-formatted CSV template.

### 4. Official Printable Academic Transcript & Grade Card
- Semester-wise breakdown of courses, credits, and awarded letter grades.
- Calculates Semester Grade Point Average (**SGPA**) and Cumulative Grade Point Average (**CGPA**).
- Print stylesheet (`@media print`) rendering official institutional letterhead, student dossier metadata, grading legend, and seal/sign-off areas.

### 5. Campus Notice Board & Circulars
- Publish official announcements categorized as `CIRCULAR`, `EXAM`, `TIMETABLE`, `EVENT`, or `URGENT`.
- Priority flags (`Standard`, `Important`, `Critical`) and audience scoping (`All Users`, `Faculty Only`, `Students Only`, or specific departments).
- Live announcement feeds integrated into all user dashboards.

### 6. Attendance & Exam Ineligibility Monitoring
- Automated detection of attendance below statutory university thresholds (<75%).
- Filter students by `Critical Shortage (<75%)`, `Warning (75–80%)`, and `Satisfactory (>80%)`.

### 7. Global Academic Record Finder
- Omnipresent search bar in navigation header matching USNs, student names, course codes, employee IDs, and cohorts in real-time.

---

## Zero-Cost Open Source Stack

- **Backend:** Python 3.11+, Django 6.x
- **Database:** SQLite (built-in default zero-config) / PostgreSQL (production-ready)
- **Frontend:** Semantic HTML5, Vanilla CSS3 (custom dark glassmorphic theme), Vanilla JavaScript
- **WSGI / Production:** Gunicorn, WhiteNoise (static file compression)
- **Containerization:** Docker & Docker Compose

---

## Quickstart & Local Installation

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/devikatd/college-lms.git
cd college-lms

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply Database Migrations

```bash
python manage.py migrate
```

### 4. Seed Demo Academic Data

Populates RV College of Engineering hierarchy, degree programs, schemes, courses, faculty, students, timetable, attendance records, marks, and notices:

```bash
python manage.py seed_academic_data
```

### 5. Launch the Development Server

```bash
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000/`.

---

## Pre-Seeded Demo Credentials

| Role | Username | Password | Dashboard URL | Description |
| :--- | :--- | :--- | :--- | :--- |
| **College Admin** | `admin` | `admin123` | `/portal/admin/` | Institutional executive management |
| **Department Admin** | `dept_admin_cs` | `pass123` | `/portal/department/` | Computer Science department ops |
| **Faculty Member** | `dr_alan` | `pass123` | `/portal/faculty/` | Teaching portal, timetable, classes |
| **Enrolled Student** | `student_rahul` | `pass123` | `/portal/student/` | Student portal, transcript, roadmap |

---

## Automated Testing Suite

The application includes an automated test suite verifying database integrity constraints, ProtectedError cascades, RBAC authorization, scheme cloning, bulk CSV import, transcript calculation, and notice filtering:

```bash
python manage.py test
```

Expected output:
```
Ran 33 tests in ...s
OK
```

---

## Production Deployment

### Option A: Docker Compose (Recommended)

```bash
docker compose up -d --build
```

The containerized service runs multi-worker Gunicorn behind port `8000` with volume persistence.

### Option B: Cloud Hosting (Heroku / Render / Railway)

The repository includes a ready-to-use [`Procfile`](file:///c:/Users/devik/OneDrive/Desktop/managementsystems/Procfile):
```
web: gunicorn lms_core.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py migrate && python manage.py seed_academic_data
```

---

## License

Open-source project built for educational administration and academic institution management.
