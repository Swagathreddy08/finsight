from datetime import date, timedelta
from fastapi.testclient import TestClient


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Recurring User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def add_charge(
    client: TestClient,
    token: str,
    description: str,
    days_ago: int,
    amount: str = "-19.99",
    merchant: str = "Stream Service",
) -> None:
    response = client.post(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": description,
            "merchant": merchant,
            "amount": amount,
            "currency": "USD",
            "category": "Subscriptions",
            "transaction_date": (date.today() - timedelta(days=days_ago)).isoformat(),
        },
    )
    assert response.status_code == 201


def test_recurring_endpoint_finds_stable_monthly_charges(client: TestClient) -> None:
    token = create_account(client, "recurring@example.com")
    add_charge(client, token, "Monthly plan", 60, "-19.00")
    add_charge(client, token, "Monthly plan", 30, "-19.99")
    add_charge(client, token, "Monthly plan", 0, "-20.00")
    add_charge(client, token, "One-off purchase", 5, merchant="Corner Shop")

    response = client.get(
        "/api/v1/analytics/recurring?months=6",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    charges = response.json()["recurring_charges"]
    assert len(charges) == 1
    assert charges[0]["name"] == "Stream Service"
    assert charges[0]["typical_amount"] == "19.99"
    assert charges[0]["occurrences"] == 3
    assert charges[0]["average_interval_days"] == 30


def test_recurring_endpoint_requires_authentication_and_limits_months(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/recurring").status_code == 401
    token = create_account(client, "recurring-validation@example.com")
    response = client.get(
        "/api/v1/analytics/recurring?months=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
