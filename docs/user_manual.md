# HR Analytics AI Report Builder — User Manual

Welcome to the **HR Analytics AI Report Builder**. This user manual explains how HR professionals, managers, and analysts can ask questions in plain English, review analytics, and download boardroom-ready reports.

---

## 1. Accessing the Platform

1. Navigate to the web application URL (e.g. `https://hr-reports.company.com` or `http://localhost:8501`).
2. Log in using your corporate credentials.
3. Your assigned role (`HR_MANAGER`, `ANALYST`, or `REPORT_VIEWER`) will automatically determine what reports and data you can view.

---

## 2. Asking Natural Language Questions

On the **Ask AI** page:
1. Select your target HR Database from the dropdown menu.
2. In the AI question box:
   > *"Show monthly employee attrition by department for 2026."*
   > *"What is the average base salary and compa-ratio by job family?"*
   > *"Show headcount breakdown by department and employment type."*
3. Click **[ Generate Report ]**.

---

## 3. Reviewing the 7-Stage Output Flow

Once generated, the system displays the report in vertical stages:
1. **Question**: The prompt you entered.
2. **Relevant Knowledge**: Institutional business rules and historical reports retrieved from the knowledge base.
3. **Generated SQL**: The dialect-adapted SQL query (can be inspected by analysts).
4. **Validation Status**: Green checkmark showing AST and security verification passed.
5. **Results Table**: Interactive tabular data preview.
6. **Charts & Visualizations**: Automatically chosen executive graphs (Line charts for time-series, Bar charts for department comparisons, Pie charts for composition).
7. **Download Report**: Export buttons to download the report in:
   - **CSV**: Raw tabular data for spreadsheets.
   - **Excel (.xlsx)**: Multi-tab formatted workbook with summary cards and metadata.
   - **PDF (.pdf)**: Boardroom-ready executive document with branded styling.

---

## 4. Managing Saved Reports

Under the **Reports** navigation tab:
- Browse previously generated organization reports.
- View version history and changes over time.
- Share reports with team members subject to role-based access control.
