from datetime import date
from fastapi.testclient import TestClient


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Category User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def create_rule(
    client: TestClient,
    token: str,
    keyword: str,
    category: str,
    priority: int = 0,
) -> dict[str, str | int]:
    response = client.post(
        "/api/v1/categorization/rules",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "keyword": keyword,
            "category": category,
            "match_field": "merchant",
            "priority": priority,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_custom_rules_override_defaults_by_priority_and_are_user_scoped(
    client: TestClient,
) -> None:
    owner_token = create_account(client, "rule-owner@example.com")
    other_token = create_account(client, "rule-other@example.com")
    create_rule(client, owner_token, "cafe", "Coffee", priority=10)
    preferred_rule = create_rule(client, owner_token, "corner", "Work meals", priority=90)

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    transaction = client.post(
        "/api/v1/transactions",
        headers=owner_headers,
        json={
            "description": "Cafe purchase",
            "merchant": "Corner Cafe",
            "amount": "-8.50",
            "currency": "USD",
            "transaction_date": date.today().isoformat(),
        },
    )
    assert transaction.status_code == 201
    assert transaction.json()["category"] == "Work meals"
    assert transaction.json()["category_source"] == "rule"

    manual = client.post(
        "/api/v1/transactions",
        headers=owner_headers,
        json={
            "description": "Cafe purchase",
            "merchant": "Corner Cafe",
            "amount": "-6.00",
            "currency": "USD",
            "category": "Personal",
            "transaction_date": date.today().isoformat(),
        },
    )
    assert manual.json()["category"] == "Personal"
    assert manual.json()["category_source"] == "manual"

    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/categorization/rules", headers=other_headers).json() == []
    other_transaction = client.post(
        "/api/v1/transactions",
        headers=other_headers,
        json={
            "description": "Cafe purchase",
            "merchant": "Corner Cafe",
            "amount": "-8.50",
            "currency": "USD",
            "transaction_date": date.today().isoformat(),
        },
    )
    assert other_transaction.json()["category"] == "Dining"
    assert other_transaction.json()["category_source"] == "automatic"
    assert preferred_rule["priority"] == 90


def test_category_feedback_is_owner_scoped(client: TestClient) -> None:
    owner_token = create_account(client, "feedback-owner@example.com")
    other_token = create_account(client, "feedback-other@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    created = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "description": "Miscellaneous purchase",
            "amount": "-11.00",
            "currency": "USD",
            "transaction_date": date.today().isoformat(),
        },
    )
    transaction_id = created.json()["id"]

    corrected = client.patch(
        f"/api/v1/transactions/{transaction_id}/category",
        headers=headers,
        json={"category": "Home supplies"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["category"] == "Home supplies"
    assert corrected.json()["category_source"] == "manual"

    hidden = client.patch(
        f"/api/v1/transactions/{transaction_id}/category",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"category": "Hidden"},
    )
    assert hidden.status_code == 404


def test_custom_rule_applies_to_csv_import_and_can_be_deleted(client: TestClient) -> None:
    token = create_account(client, "rule-import@example.com")
    rule = create_rule(client, token, "orchid", "Gifts")
    response = client.post(
        "/api/v1/transactions/import",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "custom.csv",
                "date,description,amount,merchant\n2026-11-19,Monthly order,-24.00,Orchid shop\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    transaction = client.get(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()[0]
    assert transaction["category"] == "Gifts"
    assert transaction["category_source"] == "rule"

    deleted = client.delete(
        f"/api/v1/categorization/rules/{rule['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/categorization/rules", headers={"Authorization": f"Bearer {token}"}).json() == []
