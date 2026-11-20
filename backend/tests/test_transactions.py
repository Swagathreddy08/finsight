from datetime import date
from fastapi.testclient import TestClient


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def transaction_payload() -> dict[str, str]:
    return {
        "description": "  Weekly groceries  ",
        "merchant": "  Market  ",
        "amount": "-52.40",
        "currency": "usd",
        "category": "Food",
        "transaction_date": date(2026, 11, 19).isoformat(),
    }


def test_create_and_list_transactions_for_owner(client: TestClient) -> None:
    token = create_account(client, "owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/transactions", json=transaction_payload(), headers=headers)

    assert created.status_code == 201
    data = created.json()
    assert data["description"] == "Weekly groceries"
    assert data["merchant"] == "Market"
    assert data["amount"] == "-52.40"
    assert data["currency"] == "USD"

    listed = client.get("/api/v1/transactions", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]


def test_transaction_is_not_visible_to_another_user(client: TestClient) -> None:
    owner_token = create_account(client, "first@example.com")
    other_token = create_account(client, "second@example.com")
    created = client.post(
        "/api/v1/transactions",
        json=transaction_payload(),
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    transaction_id = created.json()["id"]

    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/transactions", headers=other_headers).json() == []
    assert (
        client.get(f"/api/v1/transactions/{transaction_id}", headers=other_headers).status_code
        == 404
    )


def test_transaction_requires_authentication_and_valid_amount(client: TestClient) -> None:
    assert client.get("/api/v1/transactions").status_code == 401
    token = create_account(client, "validation@example.com")
    invalid_payload = {**transaction_payload(), "amount": "0"}
    response = client.post(
        "/api/v1/transactions",
        json=invalid_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_uncategorized_transaction_gets_a_rule_based_category(client: TestClient) -> None:
    token = create_account(client, "category@example.com")
    payload = {
        "description": "Weekly produce",
        "merchant": "Whole Foods",
        "amount": "-38.12",
        "currency": "USD",
        "transaction_date": date(2026, 11, 19).isoformat(),
    }

    response = client.post(
        "/api/v1/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["category"] == "Groceries"
