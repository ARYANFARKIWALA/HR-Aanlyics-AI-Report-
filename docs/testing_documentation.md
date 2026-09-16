# Complete Testing & Quality Control Documentation

This document describes the test strategy, structure, and execution framework for the **HR Analytics AI Report Builder**.

---

## 1. Test Categories & Organization

The test suite covers all 9 required enterprise testing categories:

1. **Unit Tests**:
   - `tests/test_category_unit.py` and `tests/test_auth.py`: Password hashing, token expiration, sanitizer rules, math utilities.
2. **Integration Tests**:
   - `tests/test_category_integration.py`: Validator token handoff to executor, analytics computation on query results.
3. **API Tests**:
   - `tests/test_category_api.py` and `tests/test_api_endpoints.py`: OpenAPI docs, health endpoints, route authentication, error responses.
4. **Database Tests**:
   - `tests/test_category_database.py` and `tests/test_database_connection.py`: Schema discovery, connection pooling, SQLite/PostgreSQL drivers.
5. **Security Tests**:
   - `tests/test_category_security.py` and `tests/test_phase7_sql_security.py`: SQL injection defense, sensitive column exfiltration blocking, Cartesian join rejection.
6. **RAG Retrieval Tests**:
   - `tests/test_category_rag.py` and `tests/test_phase5_rag.py`: Semantic context retrieval, conflict detection, score ranking.
7. **Text-to-SQL Tests**:
   - `tests/test_category_text_to_sql.py` and `tests/test_phase6_text_to_sql.py`: Dialect transpilation, anti-hallucination detection, ambiguity resolution.
8. **End-to-End Tests**:
   - `tests/test_category_e2e.py` and `tests/test_phase14_end_to_end.py`: 14-stage workflow execution for canonical attrition query.
9. **Performance Tests**:
   - `tests/test_category_performance.py`: Sub-second latency guarantees (<250ms validation, <250ms execution).

---

## 2. Running the Tests

To run the complete test suite:
```bash
pytest tests/ -v
```

To run a specific test category or phase:
```bash
# Phase 14 End-to-End Integration
pytest tests/test_phase14_end_to_end.py -v

# Phase 15 AI Evaluation Benchmark
pytest tests/test_phase15_ai_evaluation.py -v

# Phase 16 Production Deployment Tests
pytest tests/test_phase16_production_deployment.py -v
```

---

## 3. Continuous Integration (CI) Invariants

All CI builds enforce:
- Zero test failures across all suites.
- Strict read-only enforcement during query execution tests.
- Zero credentials committed in test fixtures or mock payloads.
