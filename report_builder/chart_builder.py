"""Plotly Chart Builder for Report Visualizations."""

import json
from typing import Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .schemas import ChartConfig


class ChartBuilder:
    """Constructs publication-grade Plotly interactive visualizations."""

    @classmethod
    def build_chart(cls, df: pd.DataFrame, config: ChartConfig) -> Dict[str, Any]:
        """Builds a Plotly figure dictionary from DataFrame and config."""
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title=f"{config.title} (No Data Available)",
                height=config.height
            )
            return json.loads(empty_fig.to_json())

        c_type = config.chart_type.lower()
        fig = None

        try:
            if c_type == "bar":
                if config.y_axis:
                    fig = px.bar(
                        df,
                        x=config.x_axis if config.orientation == "v" else config.y_axis,
                        y=config.y_axis if config.orientation == "v" else config.x_axis,
                        color=config.color_by,
                        orientation=config.orientation,
                        barmode=config.barmode,
                        title=config.title
                    )
                else:
                    # Value counts bar chart
                    counts = df[config.x_axis].value_counts().reset_index()
                    counts.columns = [config.x_axis, "count"]
                    fig = px.bar(
                        counts,
                        x=config.x_axis,
                        y="count",
                        title=config.title,
                        color=config.x_axis if not config.color_by else config.color_by
                    )

            elif c_type == "line":
                fig = px.line(
                    df,
                    x=config.x_axis,
                    y=config.y_axis,
                    color=config.color_by,
                    title=config.title,
                    markers=True
                )

            elif c_type in ["pie", "donut"]:
                is_donut = (c_type == "donut")
                if config.y_axis:
                    fig = px.pie(
                        df,
                        names=config.x_axis,
                        values=config.y_axis,
                        title=config.title,
                        hole=0.4 if is_donut else 0.0
                    )
                else:
                    counts = df[config.x_axis].value_counts().reset_index()
                    counts.columns = [config.x_axis, "count"]
                    fig = px.pie(
                        counts,
                        names=config.x_axis,
                        values="count",
                        title=config.title,
                        hole=0.4 if is_donut else 0.0
                    )

            elif c_type == "box":
                fig = px.box(
                    df,
                    x=config.x_axis if config.x_axis else None,
                    y=config.y_axis,
                    color=config.color_by,
                    title=config.title,
                    points="outliers"
                )

            elif c_type == "scatter":
                fig = px.scatter(
                    df,
                    x=config.x_axis,
                    y=config.y_axis,
                    color=config.color_by,
                    title=config.title,
                    trendline="ols" if len(df) > 5 and pd.api.types.is_numeric_dtype(df[config.x_axis]) else None
                )

            elif c_type == "heatmap":
                if pd.api.types.is_numeric_dtype(df[config.x_axis]) and config.y_axis and pd.api.types.is_numeric_dtype(df[config.y_axis]):
                    # Bivariate density
                    fig = px.density_heatmap(df, x=config.x_axis, y=config.y_axis, title=config.title)
                else:
                    # Categorical cross-tabulation
                    ct = pd.crosstab(df[config.x_axis], df[config.y_axis] if config.y_axis else df[config.x_axis])
                    fig = px.imshow(ct, text_auto=True, title=config.title, aspect="auto")

            else:
                # Fallback to bar
                fig = px.bar(df, x=config.x_axis, y=config.y_axis, title=config.title)

        except Exception as e:
            err_fig = go.Figure()
            err_fig.update_layout(title=f"{config.title} (Render Error: {str(e)})")
            return json.loads(err_fig.to_json())

        fig.update_layout(
            height=config.height,
            showlegend=config.show_legend,
            margin=dict(l=40, r=40, t=50, b=40),
            template="plotly_white"
        )

        return json.loads(fig.to_json())
