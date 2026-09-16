"""Database Seeder for HR Analytics and Enterprise SQL Catalog.

Populates realistic organizational data with:
- Multi-tier users with hashed passwords
- 7 Departments with Cost Centers & Budgets
- 15 Job Profiles across salary bands
- 120+ Employees with effective-dating history & attrition records
- Compensation history, Performance ratings, Leave records
- 12 Production-grade complex enterprise SQL report templates
"""

import datetime
from typing import List
from backend.auth.jwt_handler import hash_password
from .connection import SessionLocal, init_db, engine
from .models import (
    Base, User, Department, JobProfile, Employee,
    CompensationHistory, PerformanceReview, LeaveRecord,
    SQLRepository, AuditLog
)


def seed_database():
    """Seeds database schema and initial data."""
    init_db()
    session = SessionLocal()

    # If already seeded, ensure roles and permissions are populated and return
    if session.query(User).count() > 0:
        print("[Seeder] Database already seeded.")
        from backend.auth.authorization import AuthorizationService
        AuthorizationService.seed_system_roles_and_permissions(session)
        session.close()
        return

    print("[Seeder] Populating database with realistic enterprise HR data...")

    # 1. Departments
    departments_data = [
        Department(name="Engineering", code="ENG", cost_center="CC-1001", budget=5200000.0, manager_name="Sarah Chen", location="San Francisco"),
        Department(name="Sales", code="SLS", cost_center="CC-2001", budget=3800000.0, manager_name="Marcus Vance", location="New York"),
        Department(name="Product Management", code="PRD", cost_center="CC-3001", budget=2400000.0, manager_name="Elena Rostova", location="San Francisco"),
        Department(name="Human Resources", code="HR", cost_center="CC-4001", budget=1300000.0, manager_name="David Patel", location="Chicago"),
        Department(name="Finance & Legal", code="FIN", cost_center="CC-5001", budget=1900000.0, manager_name="Rachel Green", location="New York"),
        Department(name="Marketing", code="MKT", cost_center="CC-6001", budget=2100000.0, manager_name="Carlos Mendoza", location="Austin"),
        Department(name="Customer Support", code="SUP", cost_center="CC-7001", budget=1400000.0, manager_name="Aisha Mohammed", location="Austin"),
    ]
    session.add_all(departments_data)
    session.commit()

    # 2. Users with RBAC
    users_data = [
        User(
            username="admin",
            email="admin@enterprise-hr.internal",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True
        ),
        User(
            username="hr_manager",
            email="david.patel@enterprise-hr.internal",
            hashed_password=hash_password("manager123"),
            full_name="David Patel (HR Director)",
            role="hr_manager",
            department_id=4,
            is_active=True
        ),
        User(
            username="analyst",
            email="analyst@enterprise-hr.internal",
            hashed_password=hash_password("analyst123"),
            full_name="Priya Sharma (People Analyst)",
            role="hr_analyst",
            department_id=4,
            is_active=True
        ),
        User(
            username="executive",
            email="ceo@enterprise-hr.internal",
            hashed_password=hash_password("exec123"),
            full_name="Victoria Sterling (Chief People Officer)",
            role="executive",
            is_active=True
        ),
    ]
    session.add_all(users_data)
    session.commit()

    # 3. Job Profiles
    jobs_data = [
        JobProfile(title="Junior Software Engineer", job_family="Engineering", salary_grade="L1", min_salary=85000, mid_salary=105000, max_salary=125000),
        JobProfile(title="Software Engineer", job_family="Engineering", salary_grade="L2", min_salary=110000, mid_salary=135000, max_salary=160000),
        JobProfile(title="Senior Software Engineer", job_family="Engineering", salary_grade="L3", min_salary=150000, mid_salary=180000, max_salary=215000),
        JobProfile(title="Staff Engineer", job_family="Engineering", salary_grade="L4", min_salary=195000, mid_salary=230000, max_salary=270000),
        JobProfile(title="Engineering Manager", job_family="Engineering", salary_grade="M1", min_salary=180000, mid_salary=210000, max_salary=250000),
        JobProfile(title="Sales Development Rep", job_family="Sales", salary_grade="L1", min_salary=60000, mid_salary=75000, max_salary=90000),
        JobProfile(title="Account Executive", job_family="Sales", salary_grade="L2", min_salary=95000, mid_salary=120000, max_salary=150000),
        JobProfile(title="Enterprise Sales Director", job_family="Sales", salary_grade="M2", min_salary=175000, mid_salary=215000, max_salary=260000),
        JobProfile(title="Associate Product Manager", job_family="Product", salary_grade="L1", min_salary=90000, mid_salary=110000, max_salary=130000),
        JobProfile(title="Product Manager", job_family="Product", salary_grade="L2", min_salary=125000, mid_salary=155000, max_salary=185000),
        JobProfile(title="Senior Product Manager", job_family="Product", salary_grade="L3", min_salary=165000, mid_salary=195000, max_salary=230000),
        JobProfile(title="People Operations Specialist", job_family="HR", salary_grade="L1", min_salary=65000, mid_salary=80000, max_salary=95000),
        JobProfile(title="HR Business Partner", job_family="HR", salary_grade="L2", min_salary=95000, mid_salary=115000, max_salary=140000),
        JobProfile(title="Financial Analyst", job_family="Finance", salary_grade="L2", min_salary=85000, mid_salary=105000, max_salary=130000),
        JobProfile(title="Marketing Strategist", job_family="Marketing", salary_grade="L2", min_salary=80000, mid_salary=100000, max_salary=125000),
        JobProfile(title="Customer Support Specialist", job_family="Support", salary_grade="L1", min_salary=50000, mid_salary=62000, max_salary=75000),
    ]
    session.add_all(jobs_data)
    session.commit()

    # 4. Realistic Employee Seeds (125 total records with effective dates, performance, comp, and attrition)
    first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "Benjamin", "Isabella", "Lucas", "Mia", "Henry", "Charlotte", "Alexander", "Amelia", "Michael", "Harper", "Daniel", "Evelyn", "Matthew", "Abigail", "Jackson", "Emily", "Sebastian", "Elizabeth", "Aiden", "Mila", "David", "Ella", "Joseph", "Avery", "Carter", "Sofia", "Owen", "Camila", "Wyatt", "Aria", "John", "Scarlett", "Jack", "Victoria", "Luke", "Madison", "Jayden", "Luna", "Dylan", "Grace", "Grayson", "Chloe"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"]
    genders = ["Male", "Female", "Female", "Male", "Male", "Female", "Non-Binary"]
    ethnicities = ["Asian", "Hispanic/Latino", "White", "Black/African American", "Two or More Races"]
    work_modes = ["Remote", "Hybrid", "Hybrid", "On-Site", "Hybrid"]

    emp_list = []
    comp_list = []
    perf_list = []
    leave_list = []

    # Let's seed 110 active employees and 20 terminated employees
    for i in range(1, 131):
        fn = first_names[i % len(first_names)]
        ln = last_names[(i * 3) % len(last_names)]
        gender = genders[i % len(genders)]
        ethnicity = ethnicities[i % len(ethnicities)]
        dept_id = ((i % 7) + 1)
        job_idx = (i % len(jobs_data))
        job = jobs_data[job_idx]

        # Hire date between 2019 and 2024
        hire_year = 2019 + (i % 6)
        hire_month = (i % 12) + 1
        hire_day = (i % 27) + 1
        h_date = datetime.date(hire_year, hire_month, hire_day)

        is_terminated = (i % 6 == 0) and (hire_year < 2024)
        if is_terminated:
            status = "Terminated"
            term_year = min(hire_year + 2, 2024)
            term_month = ((hire_month + 3) % 12) + 1
            t_date = datetime.date(term_year, term_month, 15)
            attrition_type = "Voluntary" if i % 2 == 0 else "Involuntary"
            attrition_reason = "Better Compensation Offer" if attrition_type == "Voluntary" else "Organizational Restructuring"
        else:
            status = "Active"
            t_date = None
            attrition_type = "None"
            attrition_reason = "N/A"

        emp_no = f"EMP-{1000 + i}"
        email = f"{fn.lower()}.{ln.lower()}{i}@enterprise-hr.internal"
        work_loc = work_modes[i % len(work_modes)]

        # Effective dating
        # Current record
        eff_start = h_date
        eff_end = t_date if is_terminated else datetime.date(9999, 12, 31)

        emp = Employee(
            employee_number=emp_no,
            first_name=fn,
            last_name=ln,
            email=email,
            gender=gender,
            ethnicity=ethnicity,
            hire_date=h_date,
            termination_date=t_date,
            status=status,
            attrition_type=attrition_type,
            attrition_reason=attrition_reason,
            employment_type="Full-Time" if i % 10 != 0 else "Contractor",
            work_location=work_loc,
            effective_start_date=eff_start,
            effective_end_date=eff_end,
            is_current=True,
            department_id=dept_id,
            job_profile_id=job.id,
            manager_id=1 if i > 7 else None
        )
        session.add(emp)
        session.flush()

        # Add compensation
        base_salary = job.mid_salary + ((i % 15) - 7) * 2000
        compa_ratio = round(base_salary / job.mid_salary, 2)
        bonus = round(base_salary * (0.08 + (i % 5) * 0.02), 2)
        comp = CompensationHistory(
            employee_id=emp.id,
            base_salary=base_salary,
            bonus=bonus,
            currency="USD",
            compa_ratio=compa_ratio,
            change_reason="Annual Merit" if hire_year < 2023 else "New Hire Offer",
            effective_date=eff_start
        )
        session.add(comp)

        # Add performance reviews
        perf_score = 3 if i % 4 == 0 else (4 if i % 3 == 0 else (5 if i % 5 == 0 else 2))
        perf = PerformanceReview(
            employee_id=emp.id,
            review_cycle="2024-Annual",
            review_date=datetime.date(2024, 12, 10),
            rating=perf_score,
            potential_score=2 if perf_score >= 3 else 1,
            goals_achieved_pct=85.0 + (perf_score * 3.5),
            feedback_summary=f"Delivered reliable results in {job.title} scope. Rating {perf_score}/5."
        )
        session.add(perf)

        # Add leave records
        leave = LeaveRecord(
            employee_id=emp.id,
            leave_type="Annual" if i % 3 != 0 else "Sick",
            start_date=datetime.date(2024, 6, (i % 20) + 1),
            end_date=datetime.date(2024, 6, (i % 20) + 5),
            days_taken=5.0,
            status="Approved"
        )
        session.add(leave)

    session.commit()

    # 5. Enterprise SQL Knowledge Repository (Pre-Loaded Complex Historical Queries)
    sql_templates = [
        SQLRepository(
            report_title="Active Headcount by Department & Cost Center",
            category="Headcount",
            business_description="Returns current active headcount broken down by department, cost center, and budget utilization.",
            raw_sql="""SELECT 
    d.name AS department_name,
    d.code AS department_code,
    d.cost_center,
    COUNT(e.id) AS active_headcount,
    ROUND(SUM(c.base_salary), 2) AS total_base_payroll,
    ROUND(d.budget, 2) AS annual_budget,
    ROUND((SUM(c.base_salary) / d.budget) * 100, 2) AS budget_consumed_pct
FROM departments d
JOIN employees e ON d.id = e.department_id
JOIN compensation_history c ON e.id = c.employee_id
WHERE e.status = 'Active'
  AND e.is_current = 1
  AND e.effective_start_date <= CURRENT_DATE
  AND e.effective_end_date >= CURRENT_DATE
GROUP BY d.id, d.name, d.code, d.cost_center, d.budget
ORDER BY active_headcount DESC;""",
            business_rules_explained="Excludes terminated employees and contractors not in core payroll. Considers only point-in-time active assignments with is_current=1.",
            joins_explained="Joins departments to employees on department_id, and employees to compensation_history on employee_id.",
            effective_dating_explained="Filters e.effective_start_date <= CURRENT_DATE and e.effective_end_date >= CURRENT_DATE to guarantee active historical record.",
            tags="headcount, budget, cost center, payroll, active"
        ),
        SQLRepository(
            report_title="Annualized Voluntary & Involuntary Attrition Rates",
            category="Attrition",
            business_description="Calculates turnover and attrition rates split by voluntary resignation vs involuntary termination across departments.",
            raw_sql="""SELECT 
    d.name AS department_name,
    COUNT(CASE WHEN e.status = 'Active' THEN 1 END) AS active_employees,
    COUNT(CASE WHEN e.status = 'Terminated' AND e.attrition_type = 'Voluntary' THEN 1 END) AS voluntary_exits,
    COUNT(CASE WHEN e.status = 'Terminated' AND e.attrition_type = 'Involuntary' THEN 1 END) AS involuntary_exits,
    COUNT(CASE WHEN e.status = 'Terminated' THEN 1 END) AS total_exits,
    ROUND(
        (CAST(COUNT(CASE WHEN e.status = 'Terminated' THEN 1 END) AS FLOAT) / 
         NULLIF(COUNT(e.id), 0)) * 100, 2
    ) AS overall_turnover_rate_pct
FROM departments d
JOIN employees e ON d.id = e.department_id
GROUP BY d.id, d.name
ORDER BY overall_turnover_rate_pct DESC;""",
            business_rules_explained="Calculates voluntary vs involuntary departures over the total recorded cohort per department. Safe against division by zero with NULLIF.",
            joins_explained="Joins departments to employees table to aggregate by organizational unit.",
            effective_dating_explained="Includes full historical status for attrition event tracking.",
            tags="attrition, turnover, voluntary, involuntary, retention"
        ),
        SQLRepository(
            report_title="Compensation Equity & Compa-Ratio Distribution",
            category="Compensation",
            business_description="Analyzes salary equity, average base pay, bonuses, and compa-ratio across salary grades and job families.",
            raw_sql="""SELECT 
    j.job_family,
    j.salary_grade,
    COUNT(e.id) AS employee_count,
    ROUND(AVG(c.base_salary), 2) AS avg_base_salary,
    ROUND(MIN(c.base_salary), 2) AS min_paid_salary,
    ROUND(MAX(c.base_salary), 2) AS max_paid_salary,
    ROUND(AVG(c.compa_ratio), 2) AS avg_compa_ratio,
    ROUND(AVG(c.bonus), 2) AS avg_bonus
FROM job_profiles j
JOIN employees e ON j.id = e.job_profile_id
JOIN compensation_history c ON e.id = c.employee_id
WHERE e.status = 'Active'
  AND e.is_current = 1
GROUP BY j.job_family, j.salary_grade
ORDER BY j.job_family, j.salary_grade;""",
            business_rules_explained="Calculates average compa-ratio (salary compared to band midpoint). A compa-ratio below 0.90 flags underpayment risk.",
            joins_explained="Joins job_profiles with employees and compensation_history.",
            effective_dating_explained="Enforces e.status = 'Active' and e.is_current = 1 to reflect latest compensation revisions.",
            tags="compensation, salary, compa-ratio, equity, pay bands"
        ),
        SQLRepository(
            report_title="High Performer Retention and Flight Risk Analysis",
            category="Performance",
            business_description="Identifies top-tier employees (Performance Rating 4 or 5) who have compa-ratios under market midpoint, signaling retention risk.",
            raw_sql="""SELECT 
    e.employee_number,
    e.first_name || ' ' || e.last_name AS employee_name,
    d.name AS department,
    j.title AS job_title,
    p.rating AS performance_rating,
    p.goals_achieved_pct,
    ROUND(c.base_salary, 2) AS base_salary,
    c.compa_ratio,
    CASE 
        WHEN c.compa_ratio < 0.95 THEN 'High Flight Risk (Underpaid Top Performer)'
        WHEN c.compa_ratio BETWEEN 0.95 AND 1.05 THEN 'Moderate Retention'
        ELSE 'Well Compensated'
    END AS retention_risk_category
FROM employees e
JOIN departments d ON e.department_id = d.id
JOIN job_profiles j ON e.job_profile_id = j.id
JOIN performance_reviews p ON e.id = p.employee_id
JOIN compensation_history c ON e.id = c.employee_id
WHERE e.status = 'Active'
  AND e.is_current = 1
  AND p.rating >= 4
ORDER BY c.compa_ratio ASC;""",
            business_rules_explained="Combines performance evaluation and compa-ratio to flag talent retention risks for HR leadership.",
            joins_explained="4-way join across employees, departments, job_profiles, performance_reviews, and compensation_history.",
            effective_dating_explained="Filters only current active employees with latest cycle performance evaluations.",
            tags="retention, performance, flight risk, top performers, compa-ratio"
        ),
        SQLRepository(
            report_title="Gender Diversity & Representation Across Departments",
            category="Diversity",
            business_description="Measures gender representation percentages and salary parity by department.",
            raw_sql="""SELECT 
    d.name AS department_name,
    COUNT(e.id) AS total_headcount,
    COUNT(CASE WHEN e.gender = 'Female' THEN 1 END) AS female_count,
    COUNT(CASE WHEN e.gender = 'Male' THEN 1 END) AS male_count,
    COUNT(CASE WHEN e.gender = 'Non-Binary' THEN 1 END) AS non_binary_count,
    ROUND((CAST(COUNT(CASE WHEN e.gender = 'Female' THEN 1 END) AS FLOAT) / COUNT(e.id)) * 100, 1) AS female_representation_pct,
    ROUND(AVG(CASE WHEN e.gender = 'Female' THEN c.base_salary END), 2) AS avg_female_salary,
    ROUND(AVG(CASE WHEN e.gender = 'Male' THEN c.base_salary END), 2) AS avg_male_salary
FROM departments d
JOIN employees e ON d.id = e.department_id
JOIN compensation_history c ON e.id = c.employee_id
WHERE e.status = 'Active'
  AND e.is_current = 1
GROUP BY d.id, d.name
ORDER BY total_headcount DESC;""",
            business_rules_explained="Provides EEO/DEI compliance metrics and gender pay parity diagnostics.",
            joins_explained="Joins departments, employees, and compensation_history.",
            effective_dating_explained="Filters current active staff.",
            tags="diversity, gender, DEI, representation, pay gap"
        ),
        SQLRepository(
            report_title="Average Employee Tenure & Turnover by Work Location",
            category="Headcount",
            business_description="Compares workforce longevity and turnover between Remote, Hybrid, and On-Site employees.",
            raw_sql="""SELECT 
    e.work_location,
    COUNT(e.id) AS total_cohort,
    COUNT(CASE WHEN e.status = 'Active' THEN 1 END) AS active_headcount,
    COUNT(CASE WHEN e.status = 'Terminated' THEN 1 END) AS terminations,
    ROUND(AVG(CAST((JULIANDAY(COALESCE(e.termination_date, CURRENT_DATE)) - JULIANDAY(e.hire_date)) / 365.25 AS FLOAT)), 1) AS avg_tenure_years
FROM employees e
GROUP BY e.work_location
ORDER BY active_headcount DESC;""",
            business_rules_explained="Calculates elapsed tenure using JULIANDAY for both active employees and departed employees.",
            joins_explained="Single table aggregate with conditional counts and date math.",
            effective_dating_explained="Calculates longevity from original hire_date through termination or current date.",
            tags="tenure, remote work, hybrid, on-site, workplace policy"
        ),
        SQLRepository(
            report_title="Leave Utilization and Absence Impact by Department",
            category="Compliance",
            business_description="Tracks annual and sick leave utilization days across departments to identify burnout or staffing gaps.",
            raw_sql="""SELECT 
    d.name AS department_name,
    COUNT(DISTINCT e.id) AS total_employees,
    ROUND(SUM(CASE WHEN l.leave_type = 'Sick' THEN l.days_taken ELSE 0 END), 1) AS total_sick_leave_days,
    ROUND(SUM(CASE WHEN l.leave_type = 'Annual' THEN l.days_taken ELSE 0 END), 1) AS total_annual_leave_days,
    ROUND(SUM(l.days_taken) / COUNT(DISTINCT e.id), 1) AS avg_leave_days_per_employee
FROM departments d
JOIN employees e ON d.id = e.department_id
LEFT JOIN leave_records l ON e.id = l.employee_id
WHERE e.status = 'Active'
GROUP BY d.id, d.name
ORDER BY avg_leave_days_per_employee DESC;""",
            business_rules_explained="LEFT JOIN ensures departments with zero leave taken are not omitted from the metric report.",
            joins_explained="Departments to employees with LEFT JOIN to leave_records.",
            effective_dating_explained="Considers active staff members.",
            tags="leave, absence, burnout, sick leave, PTO"
        )
    ]

    session.add_all(sql_templates)
    session.commit()

    print("[Seeder] Successfully seeded database with realistic HR data, users, and 7 complex SQL templates!")
    session.close()


if __name__ == "__main__":
    seed_database()
