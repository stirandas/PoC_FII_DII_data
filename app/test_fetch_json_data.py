# tests/test_fetch_json_data.py
from app.services.fetch_json_data import get_fiidii_trade_json  # Import service under test. [web:347]

def test_fiidii_fetch_returns_list():
    data = get_fiidii_trade_json()  # Run the fetch. [web:347]
    assert isinstance(data, list)  # Validate JSON shape at top level. [web:343]
    assert all(isinstance(x, dict) for x in data)  # Ensure each item is an object. [web:343]
