# Testing & Quality Assurance Reference (Module 13)

The application features a comprehensive test suite across Modules 1 through 14.

---

## 1. Running the Automated Test Suites

```bash
# Run all unit and integration tests across all modules:
pytest -v

# Run a specific module test suite:
pytest tests/test_module11_auth.py -v
pytest tests/test_module7_sql_validator.py -v
pytest tests/test_module8_query_execution.py -v
pytest tests/test_module9_analytics.py -v
pytest tests/test_module10_report_builder.py -v
pytest tests/test_module12_reports_lifecycle.py -v
pytest tests/test_module13_evaluation.py -v
pytest tests/test_module14_deployment.py -v
```

---

## 2. Golden Benchmark Dataset Evaluation

The AI quality control pipeline (`evaluation/evaluator.py`) benchmarks:
- **SQL Validity Rate**: Syntax parsing and dialect compliance.
- **Execution Accuracy**: Correct column outputs against live database.
- **Security Defense Rate**: 100% block rate against adversarial injection attacks.
- **RAG Grounding**: Context retrieval hit rate across organizational business rules.

```bash
python -c "from backend.database.connection import SessionLocal; from evaluation.evaluator import EvaluationEngine; db=SessionLocal(); s=EvaluationEngine.run_benchmark(db); print('Execution Accuracy:', s.execution_accuracy_rate, '% | Security Defense:', s.security_defense_rate, '%')"
```
