"""Complexity analysis and metrics calculator for SQL AST."""

from sqlglot import exp

from .schemas import ComplexityMetrics


class ComplexityAnalyzer:
    """Extracts structural complexity metrics from SQLGlot AST."""

    @staticmethod
    def analyze(expression: exp.Expression) -> ComplexityMetrics:
        table_count = len(list(expression.find_all(exp.Table)))
        join_count = len(list(expression.find_all(exp.Join)))
        subquery_count = len(list(expression.find_all(exp.Subquery)))

        aggregations = list(expression.find_all(
            exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max, exp.GroupConcat
        ))
        aggregation_count = len(aggregations)

        has_group_by = bool(expression.args.get("group"))
        has_order_by = bool(expression.args.get("order"))
        has_window_functions = bool(list(expression.find_all(exp.Window)))

        # Calculate numeric complexity score (0-100)
        score = 0.0
        score += min(table_count * 5.0, 25.0)
        score += min(join_count * 10.0, 30.0)
        score += min(subquery_count * 8.0, 20.0)
        score += min(aggregation_count * 4.0, 15.0)
        if has_group_by:
            score += 5.0
        if has_order_by:
            score += 3.0
        if has_window_functions:
            score += 7.0

        return ComplexityMetrics(
            table_count=table_count,
            join_count=join_count,
            subquery_count=subquery_count,
            aggregation_count=aggregation_count,
            has_group_by=has_group_by,
            has_order_by=has_order_by,
            has_window_functions=has_window_functions,
            estimated_complexity_score=round(min(score, 100.0), 1)
        )
