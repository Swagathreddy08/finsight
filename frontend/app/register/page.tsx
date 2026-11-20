"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiBaseUrl, storeAuthTokens } from "../auth";

export default function RegisterPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          full_name: form.get("fullName"),
          password: form.get("password"),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Account creation failed");
      }
      storeAuthTokens(data);
      router.push("/");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account creation failed");
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
      </nav>
      <section className="auth-page">
        <div className="auth-card">
          <span className="eyebrow">New workspace</span>
          <h1>Create your account</h1>
          <p>Start building a clearer view of your finances.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              Full name
              <input name="fullName" type="text" autoComplete="name" required minLength={1} />
            </label>
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required />
            </label>
            <label>
              Password
              <input name="password" type="password" autoComplete="new-password" required minLength={12} />
            </label>
            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? "Creating account..." : "Create account"}
            </button>
            <p className="auth-message" role="alert">{message}</p>
          </form>
          <p className="auth-switch">Already registered? <a href="/login">Sign in</a></p>
        </div>
      </section>
    </main>
  );
}
