"""Master Acceptance & Integration Test Runner for Smart Classroom AV Assistant.

Executes:
1. All 13 Project Acceptance Criteria tests (test_acceptance.py)
2. All 7 Grounded RAG Retrieval tests (test_rag.py)
3. All 9 End-to-End Workflow & Lifecycle tests (test_workflow.py)
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_acceptance import TestClassroomAVAcceptance
from tests.test_rag import run_rag_tests
from tests.test_workflow import run_e2e_workflow


def run_all_tests():
    print("=" * 72)
    print("RUNNING ALL ACCEPTANCE & INTEGRATION TEST SUITES")
    print("=" * 72)

    # 1. 13 Acceptance Tests
    print("\n--- [SUITE 1/3] 13 Acceptance Criteria Tests ---")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassroomAVAcceptance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("[FAIL] Acceptance test suite failed.")
        sys.exit(1)

    # 2. RAG Retrieval & Grounding Tests
    print("\n--- [SUITE 2/3] Grounded RAG Retrieval Tests ---")
    run_rag_tests()

    # 3. Complete Workflow Tests
    print("\n--- [SUITE 3/3] End-to-End Workflow & Lifecycle Tests ---")
    run_e2e_workflow()

    print("\n" + "=" * 72)
    print("ALL TEST SUITES COMPLETED WITH 100% SUCCESS!")
    print("=" * 72)


if __name__ == "__main__":
    run_all_tests()
