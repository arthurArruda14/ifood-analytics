"""Orquestra o fluxo: pergunta -> código -> execução (com 1 retry) -> explicação."""
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.llm import explain_result, generate_code
from src.safe_exec import UnsafeCodeError, run_code

MAX_ATTEMPTS = 2


@dataclass
class Answer:
    question: str
    code: str = ""
    result: Any = None
    fig: Any = None
    explanation: str = ""
    error: str = ""
    attempts: int = 0


def result_to_text(result: Any, max_rows: int = 20) -> str:
    """Converte o resultado em texto curto para o LLM explicar."""
    if isinstance(result, pd.DataFrame):
        return result.head(max_rows).to_string(index=False)
    if isinstance(result, pd.Series):
        return result.head(max_rows).to_string()
    return str(result)


def answer_question(question: str, df: pd.DataFrame, api_key: str | None = None) -> Answer:
    """Responde uma pergunta sobre o DataFrame. Se o código falhar, tenta corrigir 1 vez."""
    answer = Answer(question=question)
    error = None
    code = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        answer.attempts = attempt
        code = generate_code(question, df, api_key, previous_error=error, previous_code=code)
        answer.code = code
        try:
            executed = run_code(code, df)
        except UnsafeCodeError as exc:
            error = str(exc)
            continue
        answer.result, answer.fig, answer.error = executed.result, executed.fig, ""
        answer.explanation = explain_result(question, result_to_text(executed.result), api_key)
        return answer

    answer.error = error or "Não foi possível gerar uma análise válida."
    return answer
