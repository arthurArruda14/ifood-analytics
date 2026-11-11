"""Carregamento de dados e gerador de pedidos sintéticos de delivery."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_PATH = DATA_DIR / "sample_orders.csv"

NEIGHBORHOODS = ["Centro", "Vila Nova", "Jardim América", "Bela Vista", "Industrial", "Santa Rita"]
CATEGORIES = ["Pizza", "Hambúrguer", "Japonesa", "Brasileira", "Saudável", "Doces", "Lanches"]
PAYMENTS = ["Pix", "Cartão de crédito", "Cartão de débito", "Dinheiro"]
WEATHER = ["Sol", "Nublado", "Chuva"]


def generate_sample_orders(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Gera pedidos fictícios com padrões realistas.

    Os atrasos aumentam com chuva, distância e horários de pico (almoço e jantar),
    para que o dashboard tenha insights de verdade para descobrir.
    """
    rng = np.random.default_rng(seed)

    days = rng.integers(0, 90, size=n)
    hours = rng.choice(
        np.arange(10, 24),
        size=n,
        p=np.array([2, 8, 14, 9, 4, 3, 4, 6, 12, 15, 12, 6, 3, 2], dtype=float) / 100,
    )
    minutes = rng.integers(0, 60, size=n)
    created_at = pd.Timestamp("2025-01-01") + pd.to_timedelta(days, unit="D")
    created_at = created_at + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m")

    weather = rng.choice(WEATHER, size=n, p=[0.5, 0.3, 0.2])
    distance = np.round(rng.gamma(shape=2.5, scale=1.6, size=n).clip(0.3, 15), 1)
    rush = np.isin(hours, [12, 13, 19, 20, 21]).astype(int)
    rain = (weather == "Chuva").astype(int)

    promised = np.round(20 + distance * 4).astype(int)
    delivery_time = promised - 4 + rng.normal(0, 5, size=n) + rush * 5 + rain * 9 + distance * 0.3
    delivery_time = np.round(delivery_time.clip(10, 120)).astype(int)

    delayed = delivery_time > promised + 5
    rating = np.clip(np.round(5 - delayed * rng.uniform(1, 2.5, n) + rng.normal(0, 0.5, n)), 1, 5)

    return pd.DataFrame(
        {
            "order_id": np.arange(1, n + 1),
            "created_at": created_at,
            "neighborhood": rng.choice(NEIGHBORHOODS, size=n),
            "restaurant_category": rng.choice(CATEGORIES, size=n),
            "order_value": np.round(rng.gamma(shape=3.0, scale=15.0, size=n) + 12, 2),
            "distance_km": distance,
            "weather": weather,
            "payment_method": rng.choice(PAYMENTS, size=n, p=[0.45, 0.3, 0.15, 0.1]),
            "promised_time_min": promised,
            "delivery_time_min": delivery_time,
            "delayed": delayed,
            "rating": rating.astype(int),
        }
    ).sort_values("created_at", ignore_index=True)


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas que parecem datas (terminam em _at, _date ou chamam 'date')."""
    for col in df.columns:
        name = col.lower()
        if name.endswith("_at") or name.endswith("_date") or name == "date":
            try:
                df[col] = pd.to_datetime(df[col])
            except (ValueError, TypeError):
                pass
    return df


def load_csv(file) -> pd.DataFrame:
    """Lê um CSV enviado pelo usuário (caminho ou arquivo)."""
    return _parse_dates(pd.read_csv(file))


def load_sample() -> pd.DataFrame:
    """Carrega o dataset de exemplo, gerando o arquivo se ele ainda não existir."""
    if not SAMPLE_PATH.exists():
        DATA_DIR.mkdir(exist_ok=True)
        generate_sample_orders().to_csv(SAMPLE_PATH, index=False)
    return load_csv(SAMPLE_PATH)


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    generate_sample_orders().to_csv(SAMPLE_PATH, index=False)
    print(f"Arquivo gerado em {SAMPLE_PATH}")
