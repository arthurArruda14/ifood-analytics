"""Execução mais segura do código gerado pela IA.

IMPORTANTE: isto reduz o risco, mas NÃO é um sandbox perfeito. Para produção,
rode o código em um contêiner isolado (Docker) com limite de tempo e memória.
"""
import ast
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "breakpoint", "help", "exit", "quit",
}
FORBIDDEN_ATTRS = {
    "eval", "system", "popen", "to_csv", "to_pickle", "to_excel", "to_parquet",
    "to_sql", "to_json", "to_hdf", "to_feather", "to_clipboard",
}

SAFE_BUILTINS = {
    name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
    for name in [
        "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list",
        "max", "min", "range", "round", "set", "sorted", "str", "sum", "tuple", "zip",
    ]
}


class UnsafeCodeError(Exception):
    """O código gerado violou uma regra de segurança ou está inválido."""


@dataclass
class ExecResult:
    result: Any
    fig: Any = None


def validate_code(code: str) -> None:
    """Analisa a árvore do código e bloqueia construções perigosas."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Erro de sintaxe no código gerado: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise UnsafeCodeError("Imports não são permitidos.")
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith("__")):
            raise UnsafeCodeError(f"Uso proibido de '{node.id}'.")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise UnsafeCodeError(f"Acesso proibido ao atributo '{node.attr}'.")
            if node.attr in FORBIDDEN_ATTRS or node.attr.startswith("read_"):
                raise UnsafeCodeError(f"Operação proibida: '{node.attr}'.")


def run_code(code: str, df: pd.DataFrame) -> ExecResult:
    """Valida e executa o código, devolvendo `result` e (opcionalmente) `fig`."""
    validate_code(code)
    namespace: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "px": px,
        "df": df.copy(),
    }
    try:
        exec(compile(code, "<llm_code>", "exec"), namespace)  # noqa: S102
    except Exception as exc:
        raise UnsafeCodeError(f"Erro ao executar o código: {type(exc).__name__}: {exc}") from exc

    if "result" not in namespace:
        raise UnsafeCodeError("O código não definiu a variável `result`.")
    return ExecResult(result=namespace["result"], fig=namespace.get("fig"))
