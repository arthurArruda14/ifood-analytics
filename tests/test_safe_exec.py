import pandas as pd
import pytest

from src.llm import extract_code
from src.safe_exec import UnsafeCodeError, run_code, validate_code


@pytest.fixture
def df():
    return pd.DataFrame({"categoria": ["A", "A", "B"], "valor": [10, 20, 30]})


def test_runs_valid_code(df):
    out = run_code('result = df.groupby("categoria")["valor"].sum()', df)
    assert out.result["A"] == 30


def test_does_not_mutate_original(df):
    run_code('df["valor"] = 0\nresult = df["valor"].sum()', df)
    assert df["valor"].sum() == 60


@pytest.mark.parametrize(
    "code",
    [
        "import os\nresult = 1",
        "result = open('/etc/passwd').read()",
        "result = df.to_csv('x.csv')",
        "result = pd.read_csv('x.csv')",
        "result = ().__class__.__bases__",
        "result = eval('1+1')",
    ],
)
def test_blocks_dangerous_code(code, df):
    with pytest.raises(UnsafeCodeError):
        run_code(code, df)


def test_requires_result_variable(df):
    with pytest.raises(UnsafeCodeError):
        run_code("x = 1", df)


def test_syntax_error_is_reported():
    with pytest.raises(UnsafeCodeError):
        validate_code("result = (")


def test_extract_code_from_markdown():
    text = "Aqui:\n```python\nresult = 1\n```\nfim"
    assert extract_code(text) == "result = 1"
