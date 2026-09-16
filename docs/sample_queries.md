# Sample Business Questions & Verified Enterprise SQL

This guide lists sample natural language questions business users can ask, together with the verified enterprise SQL templates they resolve to.

---

### 1. Employee Attrition by Department
**User Question:**
> *"Show employee attrition by department in 2026"*

**Enterprise SQL Logic:**
```sql
SELECT 
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
ORDER BY overall_turnover_rate_pct DESC;
```

---

### 2. Active Headcount & Budget Utilization
**User Question:**
> *"What is our active headcount by department and how much budget is consumed?"*

**Enterprise SQL Logic:**
```sql
SELECT 
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
ORDER BY active_headcount DESC;
```

---

### 3. Top Performer Flight Risk
**User Question:**
> *"Identify high performers who are underpaid relative to their salary band"*

**Enterprise SQL Logic:**
```sql
SELECT 
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
ORDER BY c.compa_ratio ASC;
```

---

### 4. Gender Diversity & Salary Parity
**User Question:**
> *"What is the gender representation and average salary breakdown by department?"*

**Enterprise SQL Logic:**
```sql
SELECT 
    d.name AS department_name,
    COUNT(e.id) AS total_headcount,
    COUNT(CASE WHEN e.gender = 'Female' THEN 1 END) AS female_count,
    COUNT(CASE WHEN e.gender = 'Male' THEN 1 END) AS male_count,
    ROUND((CAST(COUNT(CASE WHEN e.gender = 'Female' THEN 1 END) AS FLOAT) / COUNT(e.id)) * 100, 1) AS female_representation_pct,
    ROUND(AVG(CASE WHEN e.gender = 'Female' THEN c.base_salary END), 2) AS avg_female_salary,
    ROUND(AVG(CASE WHEN e.gender = 'Male' THEN c.base_salary END), 2) AS avg_male_salary
FROM departments d
JOIN employees e ON d.id = e.department_id
JOIN compensation_history c ON e.id = c.employee_id
WHERE e.status = 'Active'
  AND e.is_current = 1
GROUP BY d.id, d.name
ORDER BY total_headcount DESC;
```
