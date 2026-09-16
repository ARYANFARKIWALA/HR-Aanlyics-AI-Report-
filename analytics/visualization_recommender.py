"""Visualization recommender determining optimal chart types."""


from .schemas import ColumnClassification, RecommendedChart


class VisualizationRecommender:
    """Recommends executive charts based on column semantic types and data shapes."""

    @classmethod
    def recommend(cls, classifications: list[ColumnClassification]) -> list[RecommendedChart]:
        recommendations: list[RecommendedChart] = []

        date_cols = [c.column_name for c in classifications if c.semantic_type == "DATE"]
        cat_cols = [c.column_name for c in classifications if c.semantic_type == "CATEGORICAL"]
        num_cols = [c.column_name for c in classifications if c.semantic_type in ["NUMERIC", "CURRENCY"]]

        # 1. Time-series Line Chart
        if date_cols and num_cols:
            recommendations.append(RecommendedChart(
                chart_type="line",
                title=f"Temporal Trend: {num_cols[0]} over {date_cols[0]}",
                x_axis=date_cols[0],
                y_axis=num_cols[0],
                description=f"Tracks {num_cols[0]} trajectory over chronological periods."
            ))

        # 2. Categorical Comparison Bar Chart
        if cat_cols and num_cols:
            recommendations.append(RecommendedChart(
                chart_type="bar",
                title=f"{num_cols[0]} Breakdown by {cat_cols[0]}",
                x_axis=cat_cols[0],
                y_axis=num_cols[0],
                description=f"Compares {num_cols[0]} across organizational {cat_cols[0]} segments."
            ))

        # 3. Categorical Distribution Pie / Donut
        if cat_cols:
            recommendations.append(RecommendedChart(
                chart_type="pie",
                title=f"Headcount Distribution by {cat_cols[0]}",
                x_axis=cat_cols[0],
                description=f"Displays proportion of records across {cat_cols[0]} segments."
            ))

        # 4. Correlation Scatter Plot
        if len(num_cols) >= 2:
            recommendations.append(RecommendedChart(
                chart_type="scatter",
                title=f"Bivariate Correlation: {num_cols[0]} vs {num_cols[1]}",
                x_axis=num_cols[0],
                y_axis=num_cols[1],
                description=f"Inspects relationship between {num_cols[0]} and {num_cols[1]}."
            ))

        # 5. Outlier & Spread Box Plot
        if num_cols:
            recommendations.append(RecommendedChart(
                chart_type="box",
                title=f"Distribution & Spread: {num_cols[0]}",
                y_axis=num_cols[0],
                x_axis=cat_cols[0] if cat_cols else None,
                description=f"Visualizes quartiles, median, and outlier dispersion for {num_cols[0]}."
            ))

        return recommendations
