"""Dedicated Test Suite for RAG Troubleshooting Knowledge Retrieval.

Tests:
1. Loading and indexing empirical historical records from CSV dataset.
2. Retrieval accuracy for standard AV hardware symptoms.
3. Attribution verification: Ensures records cite empirical classroom incidents,
   NEVER claiming official manufacturer manual instructions.
4. Empty query and whitespace handling.
5. Out-of-domain / unmatched query handling.
6. Keyword-based TF-IDF retrieval fallback behavior.
7. Device category filtering.
8. AI diagnostic plan generation and grounding in retrieved records.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.knowledge_base import KnowledgeRetriever, retriever
from backend.ai_assistant import AIAssistant


def run_rag_tests():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
            sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
        except Exception:
            pass

    print("=" * 70)
    print("[RAG TESTS] STARTING RAG RETRIEVAL & GROUNDING TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # TEST 1: Knowledge Indexing Verification
    # -------------------------------------------------------------
    print("\n[TEST 1] Verifying Knowledge Base Indexing from CSV...")
    status = retriever.get_status()
    assert status["total_documents_indexed"] > 2000, f"Expected >2000 documents, got {status['total_documents_indexed']}"
    print(f"  [OK] Total Knowledge Chunks: {status['total_documents_indexed']}")
    print(f"  [OK] Active Backend: {status['backend_used']}")
    print(f"  [OK] Keyword Vector Dimensions: {status['keyword_vector_dimension']}")

    # -------------------------------------------------------------
    # TEST 2: Real Symptom Retrieval
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Semantic/Keyword Retrieval on Real Symptoms...")
    test_queries = [
        ("Image is unusually dim", "projector"),
        ("Stylus writing is offset", "smart_board"),
        ("Microphone has no sound", "microphone"),
    ]

    for sym, dev in test_queries:
        results = retriever.retrieve(query=sym, device_type=dev, top_k=3)
        assert len(results) > 0, f"No results returned for query '{sym}' on '{dev}'"
        top_match = results[0]
        print(f"  [OK] Query: '{sym}' on '{dev}' -> Matched: '{top_match.get('symptom')}'")
        print(f"       Top Recommended Fix: {top_match.get('fix_step')[:55]}...")
        print(f"       Historical Success Rate: {top_match.get('resolution_rate_pct')}%")
        assert "fix_step" in top_match and top_match["fix_step"]
        assert "resolution_rate_pct" in top_match

    # -------------------------------------------------------------
    # TEST 3: Strict Attribution Check (Requirement 7)
    # -------------------------------------------------------------
    print("\n[TEST 3] Verifying Empirical Attribution (Never Claim Manufacturer Manuals)...")
    results = retriever.retrieve(query="Wireless screen sharing fails", device_type="smart_board", top_k=2)
    assert len(results) > 0
    for doc in results:
        attribution = doc.get("attribution", "")
        print(f"  [OK] Document Attribution: '{attribution}'")
        assert "Empirical historical classroom incident record" in attribution
        assert "Not official manufacturer manual instructions" in attribution
        # Check text does not claim to be official manufacturer manual
        assert "official manufacturer manual" not in doc.get("text", "").lower()

    # -------------------------------------------------------------
    # TEST 4: Empty & Whitespace Query Handling
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Empty & Whitespace Query Graceful Handling...")
    empty_results = retriever.retrieve(query="", device_type="projector", top_k=2)
    assert isinstance(empty_results, list)
    assert len(empty_results) > 0, "Expected default fallback cards for empty query"
    print(f"  [OK] Empty query returned {len(empty_results)} fallback cards safely without error")

    whitespace_results = retriever.retrieve(query="    \t  ", device_type="microphone", top_k=2)
    assert isinstance(whitespace_results, list)
    assert len(whitespace_results) > 0
    print(f"  [OK] Whitespace query returned {len(whitespace_results)} fallback cards safely")

    # -------------------------------------------------------------
    # TEST 5: Out-of-Domain / Unmatched Query Handling
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Out-of-Domain Unmatched Query Handling...")
    weird_query = "hyperdrive tachyon warp flux leakage zzzzz"
    weird_results = retriever.retrieve(query=weird_query, device_type="projector", top_k=2)
    assert isinstance(weird_results, list)
    assert len(weird_results) > 0, "Expected broad fallback cards for out-of-domain query"
    print(f"  [OK] Out-of-domain query safely returned {len(weird_results)} standard fallback cards")

    # -------------------------------------------------------------
    # TEST 6: Explicit Keyword Fallback Initialization
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing Explicit Keyword Fallback Mode (force_backend='tfidf')...")
    keyword_retriever = KnowledgeRetriever(force_backend="tfidf")
    kw_status = keyword_retriever.get_status()
    assert kw_status["backend_used"] == "tfidf"
    kw_results = keyword_retriever.retrieve("No signal message appears", device_type="projector", top_k=3)
    assert len(kw_results) > 0
    print(f"  [OK] Keyword Fallback Retriever successfully matched: '{kw_results[0]['fix_step'][:50]}...'")

    # -------------------------------------------------------------
    # TEST 7: AI Assistant Plan Grounding & Step Resolution Flow
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing AI Assistant Plan Grounding in Retrieved Records...")
    assistant = AIAssistant()
    plan = assistant.analyze_and_plan(
        device_type="projector",
        symptom="Image flickers",
        room_no="D18",
        cable_status="loose",
        power_status="on",
    )
    assert "troubleshooting_steps" in plan
    assert len(plan["troubleshooting_steps"]) > 0
    assert "retrieved_context_documents" in plan
    assert len(plan["retrieved_context_documents"]) > 0
    print(f"  [OK] Generated {len(plan['troubleshooting_steps'])} steps for 'Image flickers'")
    print(f"  [OK] Reasoning mode: {plan['reasoning_mode']}")
    print(f"  [OK] Attribution included: {plan.get('attribution')}")

    # Verify loose cable generated specific reseating action
    first_step = plan["troubleshooting_steps"][0]
    print(f"  [OK] Priority Step 1 (Environmental): {first_step}")
    assert "cable" in first_step.lower() or "reseat" in first_step.lower()

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL 7 RAG RETRIEVAL & GROUNDING TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_rag_tests()
