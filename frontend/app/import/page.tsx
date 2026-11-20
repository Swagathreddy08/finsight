"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiBaseUrl, authenticatedFetch, ensureAccessToken, getAccessToken } from "../auth";

type ImportError = {
  row_number: number;
  message: string;
  raw_data: Record<string, string | null>;
};

type ImportSummary = {
  batch_id: string;
  filename: string;
  rows_total: number;
  imported_count: number;
  duplicate_count: number;
  invalid_count: number;
  errors: ImportError[];
};

export default function ImportPage() {
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    ensureAccessToken()
      .then(setHasToken)
      .catch((error: unknown) => {
        setHasToken(false);
        setMessage(error instanceof Error ? error.message : "Could not verify your session.");
      });
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSummary(null);
    setMessage("");

    const token = getAccessToken();
    const file = new FormData(event.currentTarget).get("file");
    if (!(file instanceof File) || file.size === 0) {
      setMessage("Choose a CSV file to import.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setMessage("This file is larger than the 5 MB upload limit.");
      return;
    }
    if (!token) {
      setHasToken(false);
      return;
    }

    const upload = new FormData();
    upload.append("file", file);
    setSubmitting(true);
    try {
      const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/transactions/import`, {
        method: "POST",
        body: upload,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "The CSV could not be imported.");
      }
      setSummary(data as ImportSummary);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The CSV could not be imported.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="FinSight home">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span>FinSight</span>
        </a>
        <a className="secondary-action" href="/login">Sign in</a>
      </nav>
      <section className="import-page">
        <div className="import-heading">
          <span className="eyebrow">Transaction imports</span>
          <h1>Bring your transactions in.</h1>
          <p>Upload a bank CSV and FinSight will validate each row, skip duplicates, and keep an import summary.</p>
        </div>

        {hasToken === false ? (
          <div className="import-card">
            <h2>Sign in to continue</h2>
            <p>Your transactions are kept private to your account.</p>
            <a className="primary-action" href="/login">Sign in to FinSight</a>
          </div>
        ) : (
          <div className="import-card">
            <h2>Choose a CSV file</h2>
            <p className="format-hint">
              Required columns: <code>date</code>, <code>description</code>, <code>amount</code>.
              Dates must use YYYY-MM-DD. Optional columns: merchant, currency, category.
            </p>
            <form className="import-form" onSubmit={handleSubmit}>
              <label className="file-picker">
                <span>CSV file</span>
                <input name="file" type="file" accept=".csv,text/csv" required />
              </label>
              <button className="auth-submit" type="submit" disabled={submitting || hasToken === null}>
                {submitting ? "Importing..." : "Import transactions"}
              </button>
              {message && <p className="auth-message" role="alert">{message}</p>}
            </form>

            {summary && (
              <section className="import-result" aria-live="polite">
                <h2>Import complete</h2>
                <p className="import-filename">{summary.filename}</p>
                <div className="import-counts">
                  <div><strong>{summary.imported_count}</strong><span>Imported</span></div>
                  <div><strong>{summary.duplicate_count}</strong><span>Duplicates</span></div>
                  <div><strong>{summary.invalid_count}</strong><span>Needs review</span></div>
                </div>
                {summary.errors.length > 0 && (
                  <div className="import-errors">
                    <h3>Rows to review</h3>
                    <ul>
                      {summary.errors.map((error) => (
                        <li key={`${error.row_number}-${error.message}`}>
                          <strong>Row {error.row_number}:</strong> {error.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
