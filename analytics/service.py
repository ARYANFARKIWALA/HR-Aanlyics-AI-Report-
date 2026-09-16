"""Central HR Analytics Engine Service (Module 9)."""

import uuid
import json
import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.models_analytics import AnalyticsAuditLog
from backend.database.models_execution import QueryExecutionAuditLog
from query_execution.cache import QueryCacheManager
from .schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
)
from .column_classifier import ColumnClassifier
from .profiler import DataProfiler
from .kpi_engine import KPIEngine
from .outlier_detection import OutlierDetector
from .trend_analysis import TrendAnalyzer
from .correlation import CorrelationAnalyzer
from .segmentation import SegmentationEngine
from .data_quality import DataQualityAuditor
from .visualization_recommender import VisualizationRecommender
from .insight_engine import InsightEngine


class HRAnalyticsService:
    """Orchestrates comprehensive statistical analysis, KPIs, and evidence-based insights."""

    def __init__(self, db: Session):
        self.db = db

    def analyze(
        self,
        request: AnalyticsRequest,
        user: Optional[User] = None
    ) -> AnalyticsResponse:
        """
        Processes a dataset from Module 8 or explicit payload and generates comprehensive analytics.
        HARD INVARIANT: Never queries raw database tables directly. Operates strictly on authorized datasets.
        """
        analysis_id = f"anl_{uuid.uuid4().hex}"
        df = pd.DataFrame()

        # 1. Retrieve dataset
        if request.dataset is not None:
            df = pd.DataFrame(request.dataset)
        elif request.execution_id:
            # Look up execution record
            exec_log = self.db.query(QueryExecutionAuditLog).filter(
                QueryExecutionAuditLog.execution_id == request.execution_id
            ).first()
            if exec_log:
                cached_res = QueryCacheManager.get(
                    database_id=exec_log.database_id,
                    sql_hash=exec_log.sql_hash
                )
                if cached_res:
                    df, _, _ = cached_res

        if df.empty:
            df = pd.DataFrame()

        dataset_shape = f"{len(df)} rows x {len(df.columns)} columns"

        # 2. Pipeline Execution
        classifications = ColumnClassifier.classify(df)
        profiles = DataProfiler.profile(df, classifications)
        kpis = KPIEngine.calculate_kpis(df)
        outliers = OutlierDetector.detect_outliers(df, classifications)
        trends = TrendAnalyzer.analyze_trends(df, classifications)
        correlations = CorrelationAnalyzer.analyze_correlations(df, classifications)
        segmentations = SegmentationEngine.segment(df, classifications)
        data_quality = DataQualityAuditor.audit(df)
        recommendations = VisualizationRecommender.recommend(classifications)
        insights = InsightEngine.generate_insights(
            kpis=kpis,
            outliers=outliers,
            quality=data_quality,
            segmentations=segmentations,
            correlations=correlations
        )

        # 3. Log Analytics Audit
        audit = AnalyticsAuditLog(
            analysis_id=analysis_id,
            execution_id=request.execution_id,
            user_id=user.id if user else None,
            username=user.username if user else "anonymous",
            dataset_shape=dataset_shape,
            kpis_computed=json.dumps(kpis.model_dump(), default=str),
            insights_generated_count=len(insights),
            data_quality_score=data_quality.quality_score,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        try:
            self.db.add(audit)
            self.db.commit()
        except Exception:
            self.db.rollback()

        return AnalyticsResponse(
            analysis_id=analysis_id,
            execution_id=request.execution_id,
            dataset_shape=dataset_shape,
            columns=list(df.columns),
            classifications=classifications,
            profiles=profiles,
            kpis=kpis,
            outliers=outliers,
            trends=trends,
            correlations=correlations,
            segmentations=segmentations,
            data_quality=data_quality,
            insights=insights,
            recommended_charts=recommendations
        )
