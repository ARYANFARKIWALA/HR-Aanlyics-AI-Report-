"""Deterministic narrative insight generator with exact metric citations."""


from .schemas import (
    CorrelationItem,
    DataQualityReport,
    InsightItem,
    KPISummary,
    OutlierItem,
    SegmentationBreakdown,
)


class InsightEngine:
    """Generates evidence-based narrative executive summaries citing exact computed metrics."""

    @classmethod
    def generate_insights(
        cls,
        kpis: KPISummary,
        outliers: list[OutlierItem],
        quality: DataQualityReport,
        segmentations: list[SegmentationBreakdown],
        correlations: list[CorrelationItem]
    ) -> list[InsightItem]:
        insights: list[InsightItem] = []

        # 1. Headcount & Retention Insight
        if kpis.total_records > 0 and kpis.attrition_rate_pct is not None:
            att = kpis.attrition_rate_pct
            if att > 15.0:
                insights.append(InsightItem(
                    title="Elevated Attrition Alert",
                    category="ATTRITION",
                    insight_type="ALERT",
                    text=f"The cohort reflects an elevated annualized turnover rate of {att}%, with {kpis.terminated_headcount} terminations out of {kpis.total_records} total historical records.",
                    metric_citations={"attrition_rate_pct": att, "terminated_headcount": kpis.terminated_headcount, "total_records": kpis.total_records}
                ))
            else:
                insights.append(InsightItem(
                    title="Healthy Cohort Retention",
                    category="ATTRITION",
                    insight_type="BENCHMARK",
                    text=f"Turnover remains controlled at {att}%, with {kpis.retention_rate_pct}% active retention across {kpis.active_headcount} active personnel.",
                    metric_citations={"attrition_rate_pct": att, "retention_rate_pct": kpis.retention_rate_pct}
                ))

        # 2. Compensation Insight
        if kpis.avg_compensation is not None:
            insights.append(InsightItem(
                title="Compensation Profile Summary",
                category="COMPENSATION",
                insight_type="BENCHMARK",
                text=f"Average compensation is ${kpis.avg_compensation:,.2f} with a median of ${kpis.median_compensation:,.2f}, representing a total payroll volume of ${kpis.total_payroll:,.2f}.",
                metric_citations={"avg_compensation": kpis.avg_compensation, "median_compensation": kpis.median_compensation, "total_payroll": kpis.total_payroll}
            ))

        # 3. Outlier Detection Insight
        if outliers:
            extreme_outliers = [o for o in outliers if o.severity == "EXTREME"]
            insights.append(InsightItem(
                title="Statistical Anomalies Detected",
                category="COMPENSATION",
                insight_type="ALERT",
                text=f"Identified {len(outliers)} statistical outlier records ({len(extreme_outliers)} extreme) based on IQR bounds ({outliers[0].lower_bound} to {outliers[0].upper_bound}).",
                metric_citations={"total_outliers": len(outliers), "extreme_count": len(extreme_outliers), "sample_value": outliers[0].value}
            ))

        # 4. Top Segment Insight
        if segmentations and segmentations[0].segments:
            top_dim = segmentations[0].dimension
            segs = segmentations[0].segments
            # Find largest segment by headcount
            largest_seg = max(segs.items(), key=lambda x: x[1].get("headcount", 0))
            insights.append(InsightItem(
                title=f"Dominant Concentration in {top_dim.replace('_', ' ').title()}",
                category="ORGANIZATION",
                insight_type="TREND",
                text=f"The largest concentration is '{largest_seg[0]}' comprising {largest_seg[1]['headcount']} records.",
                metric_citations={"dimension": top_dim, "segment": largest_seg[0], "headcount": largest_seg[1]["headcount"]}
            ))

        # 5. Data Quality Insight
        if quality.quality_score < 90.0:
            insights.append(InsightItem(
                title="Data Quality & Completeness Warning",
                category="DATA_QUALITY",
                insight_type="ALERT",
                text=f"Data quality index scored {quality.quality_score}/100 with {quality.anomaly_count} detected anomalies and {quality.completeness_pct}% cell completeness.",
                metric_citations={"quality_score": quality.quality_score, "anomaly_count": quality.anomaly_count}
            ))
        else:
            insights.append(InsightItem(
                title="Verified High-Fidelity Dataset",
                category="DATA_QUALITY",
                insight_type="BENCHMARK",
                text=f"Dataset verified at {quality.quality_score}/100 quality rating with {quality.completeness_pct}% completeness across {quality.total_rows} rows.",
                metric_citations={"quality_score": quality.quality_score, "completeness_pct": quality.completeness_pct}
            ))

        return insights
