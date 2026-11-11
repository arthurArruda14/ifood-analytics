"""Chamadas ao LLM (Claude): gerar código pandas e explicar o resultado."""
import os
import re
from pathlib import Path

import pandas as pd
from anthropic import Anthropic

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _client(api_key: str | None = None) -> Anthropic:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("Defina a ANTHROPIC_API_KEY no .env ou na barra lateral.")
    return Anthropic(api_key=key)


def describe_dataframe(df: pd.DataFrame, max_categories: int = 8) -> str:
    """Resume o esquema do DataFrame para o LLM (sem enviar todos os dados)."""
    lines = [f"Linhas: {len(df)}", "Colunas:"]
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
            extra = f"min={df[col].min()}, max={df[col].max()}"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            extra = f"de {df[col].min()} até {df[col].max()}"
        else:
            values = df[col].dropna().unique()[:max_categories].tolist()
            extra = f"exemplos={values}"
        lines.append(f"- {col} ({dtype}): {extra}")
    return "\n".join(lines)


def extract_code(text: str) -> str:
    """Extrai o código de dentro de um bloco ```python ... ```."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def generate_code(
    question: str,
    df: pd.DataFrame,
    api_key: str | None = None,
    previous_error: str | None = None,
    previous_code: str | None = None,
) -> str:
    """Pede ao LLM o código pandas que responde a pergunta."""
    content = f"Esquema do DataFrame `df`:\n{describe_dataframe(df)}\n\nPergunta: {question}"
    if previous_error and previous_code:
        content += (
            f"\n\nSua tentativa anterior falhou.\nCódigo:\n```python\n{previous_code}\n```\n"
            f"Erro: {previous_error}\nCorrija e responda novamente."
        )
    response = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=1000,
        system=_load_prompt("system_prompt.md"),
        messages=[{"role": "user", "content": content}],
    )
    return extract_code(response.content[0].text)


def explain_result(question: str, result_text: str, api_key: str | None = None) -> str:
    """Pede ao LLM uma explicação curta do resultado, em linguagem de negócio."""
    response = _client(api_key).messages.create(
        model=MODEL,
        max_tokens=500,
        system=_load_prompt("explain_prompt.md"),
        messages=[
            {"role": "user", "content": f"Pergunta: {question}\n\nResultado:\n{result_text}"}
        ],
    )
    return response.content[0].text.strip()
