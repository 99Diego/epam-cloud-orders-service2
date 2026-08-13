import pytest
from src.lambda_function.main import validate_order


def test_valid_order():
    valid_payload = {
        "order_id": "ORD-123",
        "customer_id": "CUST-456",
        "items": [{"item_id": "ITEM-1", "quantity": 2}],
        "total": 99.99
    }
    is_valid, reason = validate_order(valid_payload)
    assert is_valid is True
    assert reason == ""


def test_missing_order_id():
    invalid_payload = {
        "customer_id": "CUST-456",
        "items": ["item1"],
        "total": 50
    }
    is_valid, reason = validate_order(invalid_payload)
    assert is_valid is False
    assert "order_id" in reason


def test_empty_items():
    invalid_payload = {
        "order_id": "ORD-123",
        "customer_id": "CUST-456",
        "items": [],
        "total": 50
    }
    is_valid, reason = validate_order(invalid_payload)
    assert is_valid is False
    assert "items" in reason


def test_negative_total():
    invalid_payload = {
        "order_id": "ORD-123",
        "customer_id": "CUST-456",
        "items": ["item1"],
        "total": -10.0
    }
    is_valid, reason = validate_order(invalid_payload)
    assert is_valid is False
    assert "total" in reason
