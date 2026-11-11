"""Chamadas ao LLM (Claude): gerar código pandas e explicar o resultado."""
import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
from anthropic import Anthropic

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
# Modelos preferidos, em ordem. O catálogo do Groq muda com frequência, então o app
# consulta a lista da sua conta e usa o primeiro disponível. Para forçar um modelo,
# defina GROQ_MODEL no .env ou nos Secrets.
GROQ_PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]
_NOT_CHAT_MODELS = ("whisper", "guard", "tts", "orpheus", "playai", "compound", "embed")
DEFAULT_PROVIDER = "groq"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def pick_groq_model(api_key: str) -> str:
    """Escolhe um modelo de chat disponível na conta Groq da pessoa."""
    forced = os.getenv("GROQ_MODEL")
    if forced:
        return forced
    from groq import Groq

    ids = [m.id for m in Groq(api_key=api_key).models.list().data]
    chat_models = [i for i in ids if not any(bad in i.lower() for bad in _NOT_CHAT_MODELS)]
    for preferred in GROQ_PREFERRED_MODELS:
        if preferred in chat_models:
            return preferred
    if chat_models:
        return chat_models[0]
    raise ValueError("Nenhum modelo de chat disponível na sua conta Groq.")


def _chat(system: str, user: str, max_tokens: int, provider: str, api_key: str | None) -> str:
    """Envia uma mensagem ao provedor escolhido e devolve o texto da resposta."""
    if provider == "groq":
        from groq import Groq

        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("Defina a GROQ_API_KEY no .env ou na barra lateral.")
        response = Groq(api_key=key).chat.completions.create(
            model=pick_groq_model(key),
            max_tokens=max_tokens * 2,  # modelos com raciocínio gastam tokens "pensando"
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    if provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("Defina a ANTHROPIC_API_KEY no .env ou na barra lateral.")
        response = Anthropic(api_key=key).messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    raise ValueError(f"Provedor desconhecido: {provider}")


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
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def generate_code(
    question: str,
    df: pd.DataFrame,
    api_key: str | None = None,
    previous_error: str | None = None,
    previous_code: str | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> str:
    """Pede ao LLM o código pandas que responde a pergunta."""
    content = f"Esquema do DataFrame `df`:\n{describe_dataframe(df)}\n\nPergunta: {question}"
    if previous_error and previous_code:
        content += (
            f"\n\nSua tentativa anterior falhou.\nCódigo:\n```python\n{previous_code}\n```\n"
            f"Erro: {previous_error}\nCorrija e responda novamente."
        )
    text = _chat(_load_prompt("system_prompt.md"), content, 1000, provider, api_key)
    return extract_code(text)


def explain_result(
    question: str,
    result_text: str,
    api_key: str | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> str:
    """Pede ao LLM uma explicação curta do resultado, em linguagem de negócio."""
    user = f"Pergunta: {question}\n\nResultado:\n{result_text}"
    text = _chat(_load_prompt("explain_prompt.md"), user, 500, provider, api_key)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()