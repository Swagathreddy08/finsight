from datetime import date
from fastapi.testclient import TestClient


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Analytics User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def add_transaction(
    client: TestClient,
    token: str,
    *,
    amount: str,
    currency: str,
    category: str | None,
    transaction_date: str,
) -> None:
    response = client.post(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Analytics test",
            "amount": amount,
            "currency": currency,
            "category": category,
            "transaction_date": transaction_date,
        },
    )
    assert response.status_code == 201


def test_summary_groups_money_by_currency_and_filters_dates(client: TestClient) -> None:
    token = create_account(client, "analytics@example.com")
    add_transaction(
        client,
        token,
        amount="-12.50",
        currency="USD",
        category="Dining",
        transaction_date="2026-11-10",
    )
    add_transaction(
        client,
        token,
        amount="100.00",
        currency="USD",
        category=None,
        transaction_date="2026-11-12",
    )
    add_transaction(
        client,
        token,
        amount="-5.00",
        currency="USD",
        category=None,
        transaction_date="2026-11-13",
    )
    add_transaction(
        client,
        token,
        amount="-9.25",
        currency="EUR",
        category="Transport",
        transaction_date="2026-11-12",
    )
    add_transaction(
        client,
        token,
        amount="-99.00",
        currency="USD",
        category="Shopping",
        transaction_date="2026-10-31",
    )

    response = client.get(
        "/api/v1/analytics/summary?start_date=2026-11-01&end_date=2026-11-30",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    summary = response.json()
    assert summary["start_date"] == "2026-11-01"
    assert summary["end_date"] == "2026-11-30"
    by_currency = {item["currency"]: item for item in summary["currency_summaries"]}
    assert by_currency["USD"]["income"] == "100.00"
    assert by_currency["USD"]["expenses"] == "17.50"
    assert by_currency["USD"]["net"] == "82.50"
    assert by_currency["USD"]["transaction_count"] == 3
    assert by_currency["USD"]["spending_by_category"] == [
        {"category": "Dining", "amount": "12.50"},
        {"category": "Uncategorized", "amount": "5.00"},
    ]
    assert by_currency["EUR"]["expenses"] == "9.25"


def test_summary_requires_authentication_and_valid_date_order(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/summary").status_code == 401
    token = create_account(client, "analytics-validation@example.com")
    response = client.get(
        "/api/v1/analytics/summary?start_date=2026-11-20&end_date=2026-11-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_summary_is_scoped_to_the_signed_in_user(client: TestClient) -> None:
    owner_token = create_account(client, "analytics-owner@example.com")
    other_token = create_account(client, "analytics-other@example.com")
    add_transaction(
        client,
        owner_token,
        amount="-25.00",
        currency="USD",
        category="Dining",
        transaction_date=date.today().isoformat(),
    )

    response = client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200
    assert response.json()["currency_summaries"] == []
