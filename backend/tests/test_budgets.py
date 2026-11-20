from datetime import date
from fastapi.testclient import TestClient


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Budget User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_budget_progress_updates_with_month_spending(client: TestClient) -> None:
    token = create_account(client, "budget-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    month = date.today().replace(day=1)
    transaction = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "description": "Grocery bill",
            "amount": "-80.00",
            "currency": "USD",
            "category": "Groceries",
            "transaction_date": date.today().isoformat(),
        },
    )
    assert transaction.status_code == 201

    created = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "category": "Groceries",
            "currency": "usd",
            "amount": "100.00",
            "month": month.isoformat(),
        },
    )
    assert created.status_code == 201
    assert created.json()["spent"] == "80.00"
    assert created.json()["remaining"] == "20.00"
    assert created.json()["percent_used"] == "80.00"

    updated = client.put(
        f"/api/v1/budgets/{created.json()['id']}",
        headers=headers,
        json={"amount": "60.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["remaining"] == "-20.00"
    assert updated.json()["percent_used"] == "133.33"

    listed = client.get(f"/api/v1/budgets?month={month.isoformat()}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_budgets_are_unique_and_scoped_to_user(client: TestClient) -> None:
    owner_token = create_account(client, "budget-first@example.com")
    other_token = create_account(client, "budget-second@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    payload = {
        "category": "Dining",
        "currency": "USD",
        "amount": "250.00",
        "month": date.today().replace(day=1).isoformat(),
    }
    created = client.post("/api/v1/budgets", json=payload, headers=headers)
    assert created.status_code == 201
    assert client.post("/api/v1/budgets", json=payload, headers=headers).status_code == 409

    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/budgets", headers=other_headers).json() == []
    assert (
        client.put(
            f"/api/v1/budgets/{created.json()['id']}",
            headers=other_headers,
            json={"amount": "300.00"},
        ).status_code
        == 404
    )


def test_budget_rejects_non_first_day_and_zero_amount(client: TestClient) -> None:
    token = create_account(client, "budget-validation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    invalid_month = {
        "category": "Travel",
        "currency": "USD",
        "amount": "10.00",
        "month": date.today().isoformat(),
    }
    assert client.post("/api/v1/budgets", json=invalid_month, headers=headers).status_code == 422
    zero_amount = {
        **invalid_month,
        "amount": "0",
        "month": date.today().replace(day=1).isoformat(),
    }
    assert client.post("/api/v1/budgets", json=zero_amount, headers=headers).status_code == 422
