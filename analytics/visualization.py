"""Plotly Visualization Engine for HR Dashboards and Reports."""

from typing import Any, ClassVar

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class HRVisualizer:
    """Generates interactive Plotly figures for HR analytics."""

    COLOR_PALETTE: ClassVar[list[str]] = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6"]

    @classmethod
    def create_headcount_donut(cls, dept_data: list[dict[str, Any]]) -> go.Figure:
        """Donut chart for departmental active headcount."""
        if not dept_data:
            return go.Figure()
        df = pd.DataFrame(dept_data)
        fig = px.pie(
            df,
            names="department",
            values="active_headcount",
            hole=0.5,
            title="Active Headcount by Department",
            color_discrete_sequence=cls.COLOR_PALETTE
        )
        fig.update_traces(textinfo="percent+label", hoverinfo="value+name")
        fig.update_layout(showlegend=False, margin={"t": 40, "b": 20, "l": 20, "r": 20})
        return fig

    @classmethod
    def create_attrition_bar(cls, attrition_data: list[dict[str, Any]]) -> go.Figure:
        """Bar chart for turnover rate by department."""
        if not attrition_data:
            return go.Figure()
        df = pd.DataFrame(attrition_data)
        fig = px.bar(
            df,
            x="department",
            y="turnover_pct",
            color="turnover_pct",
            color_continuous_scale="Reds",
            title="Turnover Rate by Department (%)",
            labels={"turnover_pct": "Turnover %", "department": "Department"}
        )
        fig.update_layout(margin={"t": 40, "b": 20, "l": 20, "r": 20}, xaxis_tickangle=-30)
        return fig

    @classmethod
    def create_salary_boxplot(cls, df: pd.DataFrame) -> go.Figure:
        """Box plot of salary distribution by department or job family."""
        if df.empty:
            return go.Figure()

        cat_col = None
        num_col = None

        for col in df.columns:
            if col.lower() in ["department", "department_name", "job_family", "work_location", "salary_grade"]:
                cat_col = col
            if col.lower() in ["base_salary", "avg_base_salary", "salary", "total_base_payroll"]:
                num_col = col

        if cat_col and num_col:
            fig = px.box(
                df,
                x=cat_col,
                y=num_col,
                color=cat_col,
                title=f"{num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                color_discrete_sequence=cls.COLOR_PALETTE
            )
            fig.update_layout(showlegend=False, margin={"t": 40, "b": 20, "l": 20, "r": 20})
            return fig

        return cls.create_auto_chart(df, "Query Results")

    @classmethod
    def create_auto_chart(cls, df: pd.DataFrame, title: str = "Query Analysis") -> go.Figure | None:
        """Automatically selects the best chart representation for tabular SQL query results."""
        if df.empty or len(df) == 0:
            return None

        df.columns.tolist()
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

        if len(num_cols) >= 1 and len(cat_cols) >= 1:
            x_col = cat_cols[0]
            y_col = num_cols[0]

            if len(df) <= 12:
                # Bar or pie
                fig = px.bar(
                    df,
                    x=x_col,
                    y=y_col,
                    color=x_col,
                    title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    color_discrete_sequence=cls.COLOR_PALETTE
                )
                fig.update_layout(showlegend=False, margin={"t": 40, "b": 20, "l": 20, "r": 20}, xaxis_tickangle=-25)
                return fig
            else:
                # Line or scatter
                fig = px.line(
                    df,
                    x=x_col,
                    y=y_col,
                    title=f"{y_col.replace('_', ' ').title()} Trend across {x_col.replace('_', ' ').title()}"
                )
                fig.update_layout(margin={"t": 40, "b": 20, "l": 20, "r": 20})
                return fig

        elif len(num_cols) >= 2:
            fig = px.scatter(
                df,
                x=num_cols[0],
                y=num_cols[1],
                title=f"Correlation: {num_cols[0]} vs {num_cols[1]}"
            )
            fig.update_layout(margin={"t": 40, "b": 20, "l": 20, "r": 20})
            return fig

        return None
