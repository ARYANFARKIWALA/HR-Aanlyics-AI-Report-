# End-User Guide: HR Analytics AI Report Builder

Welcome to the HR Analytics AI Report Builder. This guide explains how HR business partners, managers, and analysts can utilize the platform to generate reports and extract data insights.

---

## 1. Logging In & Navigation

1. Navigate to the application URL: `http://localhost:8501` (or your company's production domain).
2. Enter your credentials on the login screen.
3. Access modules via the left sidebar:
   - **Database Connection**: Select or register an HR database.
   - **AI Report Builder**: Convert natural language questions to verified SQL and charts.
   - **HR Analytics**: Explore automatic statistical breakdowns, turnover rates, and compa-ratios.
   - **Report Catalog & Export**: Browse saved reports, manage versions, and export to CSV, Excel, or PDF.

---

## 2. Asking a Reporting Question

1. Open **AI Report Builder**.
2. Type your question in natural language, for example:
   - *"What is the active headcount breakdown by department?"*
   - *"Show voluntary vs involuntary turnover rate for the last fiscal year."*
   - *"Compare average base salary and compa-ratio across engineering job profiles."*
3. Click **Generate Report**.
4. The system retrieves relevant business rules, formulates a query plan, validates the SQL for safety, executes the query, and presents interactive Plotly charts and KPI summary cards.

---

## 3. Saving & Exporting Reports

1. Under the generated report, click **Save Report to Catalog**.
2. Give the report a title and select a category.
3. In **Report Catalog & Export**, you can download:
   - **CSV**: Raw tabular data with Column-Level Security (sensitive columns masked for non-PII roles).
   - **Excel (.xlsx)**: Corporate multi-tab workbook with Executive Summary, Data, and Governance Lineage tabs.
   - **PDF**: Boardroom-ready landscape document with branded headers, KPI cards, and formatted data tables.
