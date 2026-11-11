import pandas as pd

from src import llm, pipeline


def test_retry_fixes_failed_code(monkeypatch):
    """Primeira resposta do 'LLM' falha; a segunda corrige. O pipeline deve se recuperar."""
    replies = iter(
        [
            "```python\nresult = df['coluna_inexistente'].sum()\n```",
            "```python\nresult = df['valor'].sum()\n```",
            "O total é 60.",
        ]
    )
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: next(replies))

    df = pd.DataFrame({"valor": [10, 20, 30]})
    answer = pipeline.answer_question("qual o total?", df, api_key="x", provider="groq")

    assert answer.error == ""
    assert answer.attempts == 2
    assert answer.result == 60
    assert "60" in answer.explanation


def test_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: "```python\nimport os\n```")
    df = pd.DataFrame({"valor": [1]})
    answer = pipeline.answer_question("x", df, api_key="x")
    assert answer.error
    assert answer.attempts == pipeline.MAX_ATTEMPTS
