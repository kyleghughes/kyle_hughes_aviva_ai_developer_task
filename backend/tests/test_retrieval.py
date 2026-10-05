import pytest

from app.retrieval import (
    is_workload_question,
    retrieve,
    workload_evidence,
)


@pytest.mark.parametrize(
    "question",
    [
        "What should I prioritise?",
        "What needs my attention first?",
        "Show me my priorities",
        "Which emails are urgent?",
    ],
)
def test_workload_question_detection(question):
    assert is_workload_question(question)


def test_unrelated_question_is_not_workload_question():
    assert not is_workload_question("What colour is the sky?")


def test_retrieve_ranks_by_term_frequency(ingested_service):
    ids = retrieve(ingested_service.repo, "claim")
    assert ids
    assert len(ids) <= 8


def test_retrieve_returns_empty_for_stopwords_only(ingested_service):
    assert retrieve(ingested_service.repo, "what is the email") == []


def test_workload_evidence_excludes_done(ingested_service):
    first = next(iter(ingested_service.repo.work_items))
    ingested_service.repo.set_done(first, True)

    ids, evidence = workload_evidence(ingested_service.repo)

    assert first not in ids
    assert f"THREAD {first}" not in evidence
