"""FastAPI REST routes for Module 13 - Testing, Evaluation & AI Quality Control."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.auth.dependencies import get_current_user
from backend.auth.authorization import AuthorizationService
from evaluation.schemas import (
    EvaluationSummary,
    EvaluationRunRequest,
    AdversarialTestResult
)
from evaluation.evaluator import EvaluationEngine
from evaluation.adversarial_runner import AdversarialSecurityRunner

router = APIRouter(prefix="/api/evaluation", tags=["Module 13 - AI Quality Control & Evaluation"])


@router.post("/run", response_model=EvaluationSummary)
def run_evaluation(
    request: Optional[EvaluationRunRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes the full or categorized golden dataset evaluation benchmark."""
    # Check that user has administrative or analytics viewing rights
    if getattr(current_user, "role", "") not in ["admin", "hr_manager"]:
        if not AuthorizationService.has_permission(db, current_user, "admin:audit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin clearance required to run system evaluation benchmarks."
            )

    summary = EvaluationEngine.run_benchmark(db=db, req=request)
    return summary


@router.get("/latest", response_model=Optional[EvaluationSummary])
def get_latest_evaluation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the most recent evaluation scorecard, running one if not yet run."""
    summary = EvaluationEngine.get_latest_summary()
    if not summary:
        summary = EvaluationEngine.run_benchmark(db=db)
    return summary


@router.get("/golden-dataset", response_model=List[Dict[str, Any]])
def get_golden_dataset(
    current_user: User = Depends(get_current_user),
):
    """Returns curated test cases from the golden benchmark dataset."""
    return EvaluationEngine.load_golden_dataset()


@router.post("/adversarial", response_model=List[AdversarialTestResult])
def run_adversarial_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes the penetration and prompt injection stress test suite."""
    if getattr(current_user, "role", "") not in ["admin", "hr_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin clearance required to run adversarial penetration tests."
        )

    results = AdversarialSecurityRunner.run_penetration_tests(db=db)
    return results
