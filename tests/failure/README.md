# Section 9 Failure Matrix Integration Tests Mapping

This document maps each integration test module in the `tests/` directory to its corresponding failure-matrix row in `anchor-spec.md` Section 9.

| Section 9 Failure Mode / Row | Test Module | Description |
| :--- | :--- | :--- |
| **Worker killed mid-step** | [`tests/failure/test_kill_and_resume.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_kill_and_resume.py) | Asserts that when a worker is killed mid-step, another worker claims, replays, and resumes. |
| **Worker stalls but is alive** | [`tests/failure/test_zombie_worker_fenced.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_zombie_worker_fenced.py) | Asserts that a zombie worker is fenced on write and withdraws. |
| **Crash between tool intent and result** | [`tests/failure/test_uncertainty_window.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_uncertainty_window.py) | Asserts the behavior of uncertainty window policies on crash. |
| **Two workers race to claim run** | [`tests/failure/test_two_workers_race_same_run.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_two_workers_race_same_run.py) | Asserts row locking prevents duplicate claims under worker races. |
| **Duplicate event append** | [`tests/failure/test_duplicate_seq_under_contention.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_duplicate_seq_under_contention.py) | Asserts that database unique constraint catches duplicate seq appends. |
| **Step fails transiently** | [`tests/unit/test_retry_backoff_jitter.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_retry_backoff_jitter.py) | Asserts backoff interval calculation adheres to jitter and cap bounds. |
| **Step fails permanently** | *Fold check* | Covered by log-derived folds and reconstruction tests. |
| **Database unavailable** | [`tests/failure/test_health_db_unreachable.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_health_db_unreachable.py) | Asserts that health endpoint reports 503 and degrades gracefully when database is unreachable. |
| **Clock skew between workers** | [`tests/unit/test_lease_expiry_uses_db_clock.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_lease_expiry_uses_db_clock.py) | Asserts lease expiration evaluates against the database clock exclusively. |
| **Fleet saturated** | [`tests/unit/test_global_cap_enforced_at_claim.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_global_cap_enforced_at_claim.py) | Asserts the global capacity limit prevents excessive active claims. |
| **Worker registers then dies** | [`tests/unit/test_worker_registration.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_worker_registration.py) | Asserts worker row insertion and stale heartbeat tracking. |
