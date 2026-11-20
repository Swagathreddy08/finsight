"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiBaseUrl, authenticatedFetch, clearAuthTokens, getAccessToken, revokeSession } from "../auth";

type CategorySpending = {
  category: string;
  amount: string | number;
};

type CurrencySummary = {
  currency: string;
  income: string | number;
  expenses: string | number;
  net: string | number;
  transaction_count: number;
  spending_by_category: CategorySpending[];
};

type AnalyticsSummary = {
  start_date: string;
  end_date: string;
  currency_summaries: CurrencySummary[];
};

type Transaction = {
  id: string;
  description: string;
  merchant: string | null;
  amount: string | number;
  currency: string;
  category: string | null;
  category_source: string | null;
  transaction_date: string;
};

type CategorizationRule = {
  id: string;
  keyword: string;
  category: string;
  match_field: "any" | "merchant" | "description";
  priority: number;
};

type BudgetProgress = {
  id: string;
  category: string;
  currency: string;
  month: string;
  budget_amount: string | number;
  spent: string | number;
  remaining: string | number;
  percent_used: string | number;
};

type RecurringCharge = {
  name: string;
  currency: string;
  typical_amount: string | number;
  category: string | null;
  last_seen: string;
  occurrences: number;
  average_interval_days: number;
};

type DashboardData = {
  analytics: AnalyticsSummary;
  transactions: Transaction[];
  budgets: BudgetProgress[];
  recurringCharges: RecurringCharge[];
  rules: CategorizationRule[];
};

const formatAmount = (amount: string | number, currency: string) =>
  `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(Number(amount))} ${currency}`;
const categoryOptions = [
  "Groceries",
  "Dining",
  "Housing",
  "Utilities",
  "Transportation",
  "Healthcare",
  "Subscriptions",
  "Entertainment",
  "Shopping",
  "Income",
  "Uncategorized",
];

function CategoryEditor({
  transaction,
  onSaved,
}: {
  transaction: Transaction;
  onSaved: (transaction: Transaction) => void;
}) {
  const [category, setCategory] = useState(transaction.category || "Uncategorized");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token) {
      setMessage("Sign in again to update this category.");
      return;
    }

    setSaving(true);
    setMessage("");
    try {
      const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/transactions/${transaction.id}/category`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: category === "Uncategorized" ? null : category }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Could not update category.");
      onSaved(result as Transaction);
      setMessage("Saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update category.");
    } finally {
      setSaving(false);
    }
  }

  const options = Array.from(new Set([
    ...categoryOptions,
    ...(transaction.category ? [transaction.category] : []),
  ]));

  return (
    <form className="category-editor" onSubmit={saveCategory}>
      <label>
        Category
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          {options.map((option) => <option key={option}>{option}</option>)}
        </select>
      </label>
      <button type="submit" disabled={saving}>{saving ? "Saving..." : "Save"}</button>
      {message && <small role="status">{message}</small>}
    </form>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [message, setMessage] = useState("");
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingBudget, setSavingBudget] = useState(false);
  const [budgetMessage, setBudgetMessage] = useState("");
  const [savingRule, setSavingRule] = useState(false);
  const [ruleMessage, setRuleMessage] = useState("");

  useEffect(() => {
    Promise.all([
      authenticatedFetch(`${apiBaseUrl}/api/v1/analytics/summary`),
      authenticatedFetch(`${apiBaseUrl}/api/v1/transactions?limit=8`),
      authenticatedFetch(`${apiBaseUrl}/api/v1/budgets`),
      authenticatedFetch(`${apiBaseUrl}/api/v1/analytics/recurring`),
      authenticatedFetch(`${apiBaseUrl}/api/v1/categorization/rules`),
    ])
      .then(async ([analyticsResponse, transactionsResponse, budgetsResponse, recurringResponse, rulesResponse]) => {
        const responses = [analyticsResponse, transactionsResponse, budgetsResponse, recurringResponse, rulesResponse];
        if (responses.some((response) => response.status === 401)) {
          clearAuthTokens();
          setNeedsSignIn(true);
          return null;
        }
        const [analyticsData, transactionsData, budgetsData, recurringData, rulesData] = await Promise.all([
          analyticsResponse.json(),
          transactionsResponse.json(),
          budgetsResponse.json(),
          recurringResponse.json(),
          rulesResponse.json(),
        ]);
        const failedResponse = responses.find((response) => !response.ok);
        if (failedResponse) {
          const errorData = [analyticsData, transactionsData, budgetsData, recurringData, rulesData][responses.indexOf(failedResponse)];
          throw new Error(errorData.detail || "Could not load your dashboard.");
        }
        return {
          analytics: analyticsData as AnalyticsSummary,
          transactions: transactionsData as Transaction[],
          budgets: budgetsData as BudgetProgress[],
          recurringCharges: recurringData.recurring_charges as RecurringCharge[],
          rules: rulesData as CategorizationRule[],
        };
      })
      .then((result) => {
        if (result) setData(result);
      })
      .catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : "Could not load your dashboard.");
      })
      .finally(() => setLoading(false));
  }, []);

  async function saveBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBudgetMessage("");
    const formElement = event.currentTarget;
    const token = getAccessToken();
    if (!token || !data) {
      setNeedsSignIn(true);
      return;
    }

    const form = new FormData(formElement);
    const category = String(form.get("category") || "").trim();
    const currency = String(form.get("currency") || "USD").toUpperCase();
    const amount = String(form.get("amount") || "");
    const existing = data.budgets.find(
      (budget) => budget.category.toLowerCase() === category.toLowerCase() && budget.currency === currency,
    );
    setSavingBudget(true);
    try {
      const response = await authenticatedFetch(
        existing ? `${apiBaseUrl}/api/v1/budgets/${existing.id}` : `${apiBaseUrl}/api/v1/budgets`,
        {
          method: existing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(existing ? { amount } : { category, currency, amount }),
        },
      );
      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(responseData.detail || "Could not save your budget.");
      }

      const refreshed = await authenticatedFetch(`${apiBaseUrl}/api/v1/budgets`);
      const budgetList = await refreshed.json();
      if (!refreshed.ok) {
        throw new Error(budgetList.detail || "Budget saved, but the list could not be refreshed.");
      }
      setData((current) => current ? { ...current, budgets: budgetList as BudgetProgress[] } : current);
      formElement.reset();
      setBudgetMessage(existing ? "Budget updated." : "Budget added.");
    } catch (error) {
      setBudgetMessage(error instanceof Error ? error.message : "Could not save your budget.");
    } finally {
      setSavingBudget(false);
    }
  }

  async function saveRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRuleMessage("");
    const formElement = event.currentTarget;
    const token = getAccessToken();
    if (!token || !data) {
      setNeedsSignIn(true);
      return;
    }
    const form = new FormData(formElement);
    const payload = {
      keyword: String(form.get("keyword") || "").trim(),
      category: String(form.get("ruleCategory") || "").trim(),
      match_field: String(form.get("matchField") || "any"),
      priority: Number(form.get("priority") || 0),
    };
    setSavingRule(true);
    try {
      const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/categorization/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Could not save your rule.");
      const refreshed = await authenticatedFetch(`${apiBaseUrl}/api/v1/categorization/rules`);
      const ruleList = await refreshed.json();
      if (!refreshed.ok) throw new Error(ruleList.detail || "Rule saved, but the list could not be refreshed.");
      setData((current) => current ? { ...current, rules: ruleList as CategorizationRule[] } : current);
      formElement.reset();
      setRuleMessage("Rule added. It will be used for new transactions and imports.");
    } catch (error) {
      setRuleMessage(error instanceof Error ? error.message : "Could not save your rule.");
    } finally {
      setSavingRule(false);
    }
  }

  async function deleteRule(ruleId: string) {
    const token = getAccessToken();
    if (!token) return;
    setRuleMessage("");
    try {
      const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/categorization/rules/${ruleId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || "Could not delete the rule.");
      }
      setData((current) => current
        ? { ...current, rules: current.rules.filter((rule) => rule.id !== ruleId) }
        : current);
      setRuleMessage("Rule removed.");
    } catch (error) {
      setRuleMessage(error instanceof Error ? error.message : "Could not delete the rule.");
    }
  }

  function updateTransaction(transaction: Transaction) {
    setData((current) => current
      ? {
          ...current,
          transactions: current.transactions.map((item) => item.id === transaction.id ? transaction : item),
        }
      : current);
  }

  async function handleSignOut() {
    try {
      await revokeSession();
      window.location.href = "/login";
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not revoke the current session.");
    }
  }

  return (
    <main className="page-shell">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="FinSight home">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span>FinSight</span>
        </a>
        <div className="dashboard-nav">
          <a href="/import">Import CSV</a>
          {data
            ? <button className="secondary-action" type="button" onClick={handleSignOut}>Sign out</button>
            : <a href="/login">Sign in</a>}
        </div>
      </nav>

      <section className="dashboard-page">
        <div className="dashboard-heading">
          <div>
            <span className="eyebrow">Your finances at a glance</span>
            <h1>Dashboard</h1>
          </div>
          {data && (
            <span className="dashboard-period">
              {data.analytics.start_date} – {data.analytics.end_date}
            </span>
          )}
        </div>

        {loading && <p className="dashboard-state" role="status">Loading your financial overview...</p>}
        {message && <p className="dashboard-state dashboard-error" role="alert">{message}</p>}
        {needsSignIn && (
          <div className="dashboard-empty">
            <h2>Sign in to see your finances</h2>
            <p>Your dashboard is private to your account.</p>
            <a className="primary-action" href="/login">Sign in to FinSight</a>
          </div>
        )}
        {data && (
          <>
            {data.analytics.currency_summaries.length === 0 ? (
              <div className="dashboard-empty">
                <h2>No transactions in this period yet</h2>
                <p>Add one directly or import a CSV to start exploring your spending.</p>
                <a className="primary-action" href="/import">Import a CSV</a>
              </div>
            ) : (
              <div className="currency-sections">
                {data.analytics.currency_summaries.map((summary) => {
                  const largestCategory = Math.max(
                    1,
                    ...summary.spending_by_category.map((item) => Number(item.amount)),
                  );
                  return (
                    <section className="currency-section" key={summary.currency} aria-label={`${summary.currency} summary`}>
                      <h2>{summary.currency} overview</h2>
                      <div className="summary-cards">
                        <article><span>Income</span><strong>{formatAmount(summary.income, summary.currency)}</strong></article>
                        <article><span>Spent</span><strong>{formatAmount(summary.expenses, summary.currency)}</strong></article>
                        <article><span>Net</span><strong>{formatAmount(summary.net, summary.currency)}</strong></article>
                        <article><span>Transactions</span><strong>{summary.transaction_count}</strong></article>
                      </div>
                      <div className="dashboard-panels">
                        <section className="dashboard-panel">
                          <h3>Spending by category</h3>
                          {summary.spending_by_category.length === 0 ? (
                            <p className="empty-note">No expenses in this period.</p>
                          ) : (
                            <ul className="category-list">
                              {summary.spending_by_category.map((item) => (
                                <li key={item.category}>
                                  <div className="category-label">
                                    <span>{item.category}</span>
                                    <strong>{formatAmount(item.amount, summary.currency)}</strong>
                                  </div>
                                  <span className="category-track">
                                    <span style={{ width: `${(Number(item.amount) / largestCategory) * 100}%` }} />
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </section>
                      </div>
                    </section>
                  );
                })}
              </div>
            )}

            <section className="dashboard-panel planning-panel">
              <div className="panel-heading">
                <h2>Monthly budgets</h2>
                <span>{new Date().toLocaleDateString(undefined, { month: "long", year: "numeric" })}</span>
              </div>
              <form className="budget-form" onSubmit={saveBudget}>
                <label>
                  Category
                  <input name="category" type="text" maxLength={80} required placeholder="e.g. Groceries" />
                </label>
                <label>
                  Monthly limit
                  <input name="amount" type="number" min="0.01" step="0.01" required placeholder="500.00" />
                </label>
                <label>
                  Currency
                  <input name="currency" type="text" minLength={3} maxLength={3} defaultValue="USD" required />
                </label>
                <button className="auth-submit" type="submit" disabled={savingBudget}>
                  {savingBudget ? "Saving..." : "Save budget"}
                </button>
                {budgetMessage && <p className="budget-message" role="status">{budgetMessage}</p>}
              </form>
              {data.budgets.length === 0 ? (
                <p className="empty-note">Set a monthly category limit to start tracking your progress.</p>
              ) : (
                <ul className="budget-list">
                  {data.budgets.map((budget) => {
                    const used = Math.max(0, Number(budget.percent_used));
                    return (
                      <li key={budget.id}>
                        <div className="category-label">
                          <span>{budget.category} · {budget.currency}</span>
                          <strong>{formatAmount(budget.spent, budget.currency)} of {formatAmount(budget.budget_amount, budget.currency)}</strong>
                        </div>
                        <span className="category-track">
                          <span className={used > 100 ? "over-budget" : ""} style={{ width: `${Math.min(100, used)}%` }} />
                        </span>
                        <small className={Number(budget.remaining) < 0 ? "over-budget-note" : ""}>
                          {Number(budget.remaining) < 0
                            ? `${formatAmount(Math.abs(Number(budget.remaining)), budget.currency)} over budget`
                            : `${formatAmount(budget.remaining, budget.currency)} remaining`}
                        </small>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="dashboard-panel planning-panel">
              <div className="panel-heading">
                <h2>Possible recurring charges</h2>
                <span>Last 6 months</span>
              </div>
              {data.recurringCharges.length === 0 ? (
                <p className="empty-note">No likely monthly charges found yet. We need at least three similar payments.</p>
              ) : (
                <ul className="transaction-list">
                  {data.recurringCharges.map((charge) => (
                    <li key={`${charge.currency}-${charge.name}`}>
                      <div>
                        <strong>{charge.name}</strong>
                        <span>{charge.category || "Uncategorized"} · about every {charge.average_interval_days} days · last seen {charge.last_seen}</span>
                      </div>
                      <strong>{formatAmount(charge.typical_amount, charge.currency)}</strong>
                    </li>
                  ))}
                </ul>
              )}
              <p className="recurring-note">These are estimates based on repeated, similar payments. Check each one before acting.</p>
            </section>

            <section className="dashboard-panel planning-panel">
              <div className="panel-heading">
                <h2>Your categorization rules</h2>
                <span>Applied to new transactions</span>
              </div>
              <form className="rule-form" onSubmit={saveRule}>
                <label>
                  Match keyword
                  <input name="keyword" type="text" maxLength={100} required placeholder="e.g. Corner Cafe" />
                </label>
                <label>
                  Assign category
                  <input name="ruleCategory" type="text" maxLength={80} required placeholder="e.g. Coffee" />
                </label>
                <label>
                  Look in
                  <select name="matchField" defaultValue="any">
                    <option value="any">Merchant or description</option>
                    <option value="merchant">Merchant</option>
                    <option value="description">Description</option>
                  </select>
                </label>
                <label>
                  Priority
                  <input name="priority" type="number" min="0" max="100" defaultValue="50" />
                </label>
                <button className="auth-submit" type="submit" disabled={savingRule}>
                  {savingRule ? "Saving..." : "Add rule"}
                </button>
                {ruleMessage && <p className="budget-message" role="status">{ruleMessage}</p>}
              </form>
              {data.rules.length === 0 ? (
                <p className="empty-note">Add a merchant or description keyword to make categorization fit your habits.</p>
              ) : (
                <ul className="rule-list">
                  {data.rules.map((rule) => (
                    <li key={rule.id}>
                      <div>
                        <strong>{rule.keyword}</strong>
                        <span>{rule.match_field} → {rule.category} · priority {rule.priority}</span>
                      </div>
                      <button type="button" onClick={() => deleteRule(rule.id)}>Remove</button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="dashboard-panel recent-transactions">
              <div className="panel-heading">
                <h2>Recent transactions</h2>
                <a href="/import">Import more</a>
              </div>
              {data.transactions.length === 0 ? (
                <p className="empty-note">Your transactions will show up here.</p>
              ) : (
                <ul className="transaction-list">
                  {data.transactions.map((transaction) => (
                    <li key={transaction.id}>
                      <div>
                        <strong>{transaction.merchant || transaction.description}</strong>
                        <span>{transaction.category || "Uncategorized"} · {transaction.transaction_date}</span>
                        <CategoryEditor
                          key={`${transaction.id}-${transaction.category || "none"}`}
                          transaction={transaction}
                          onSaved={updateTransaction}
                        />
                      </div>
                      <strong>{formatAmount(transaction.amount, transaction.currency)}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </section>
    </main>
  );
}
