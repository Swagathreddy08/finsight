from fastapi.testclient import TestClient

from app.models.transaction_import import TransactionImportError
from sqlalchemy import select


def create_account(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Import User",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_csv_import_saves_valid_rows_and_reports_duplicates_and_errors(
    client: TestClient,
    db_session,
) -> None:
    token = create_account(client, "csv-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    csv_content = (
        "date,description,amount,merchant,currency,category\n"
        "2026-11-19,Coffee,-4.50,Corner Cafe,usd,\n"
        "2026-11-19,Coffee,-4.50,Corner Cafe,USD,\n"
        "not-a-date,Invalid row,not-money,,USD,\n"
    )

    response = client.post(
        "/api/v1/transactions/import",
        headers=headers,
        files={"file": ("bank.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    summary = response.json()
    assert summary["rows_total"] == 3
    assert summary["imported_count"] == 1
    assert summary["duplicate_count"] == 1
    assert summary["invalid_count"] == 1
    assert summary["errors"][0]["row_number"] == 4
    assert summary["errors"][0]["raw_data"]["description"] == "Invalid row"
    transactions = client.get("/api/v1/transactions", headers=headers).json()
    assert transactions[0]["category"] == "Dining"

    details = client.get(
        f"/api/v1/transactions/imports/{summary['batch_id']}",
        headers=headers,
    )
    assert details.status_code == 200
    assert details.json()["errors"][0]["message"]

    stored_error = db_session.scalar(
        select(TransactionImportError).where(TransactionImportError.import_id == summary["batch_id"])
    )
    assert stored_error is not None
    assert stored_error.raw_data["amount"] == "not-money"

    repeated = client.post(
        "/api/v1/transactions/import",
        headers=headers,
        files={"file": ("bank.csv", csv_content, "text/csv")},
    )
    assert repeated.status_code == 201
    assert repeated.json()["imported_count"] == 0
    assert repeated.json()["duplicate_count"] == 2


def test_import_history_is_scoped_to_owner(client: TestClient) -> None:
    owner_token = create_account(client, "csv-first@example.com")
    other_token = create_account(client, "csv-second@example.com")
    upload = client.post(
        "/api/v1/transactions/import",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("empty-rows.csv", "date,description,amount\n", "text/csv")},
    )
    batch_id = upload.json()["batch_id"]

    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/transactions/imports", headers=other_headers).json() == []
    assert (
        client.get(f"/api/v1/transactions/imports/{batch_id}", headers=other_headers).status_code
        == 404
    )


def test_csv_import_rejects_bad_headers_and_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/transactions/import").status_code == 401
    token = create_account(client, "csv-validation@example.com")
    response = client.post(
        "/api/v1/transactions/import",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("missing-columns.csv", "memo,value\nCoffee,-4.50\n", "text/csv")},
    )
    assert response.status_code == 422
