from src.data import generate_sample_orders


def test_sample_shape_and_columns():
    df = generate_sample_orders(n=500)
    assert len(df) == 500
    assert {"order_id", "created_at", "delayed", "delivery_time_min", "rating"} <= set(df.columns)


def test_rain_increases_delays():
    df = generate_sample_orders(n=5000)
    rain = df[df["weather"] == "Chuva"]["delayed"].mean()
    sun = df[df["weather"] == "Sol"]["delayed"].mean()
    assert rain > sun
