"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiBaseUrl, storeAuthTokens } from "../auth";

export default function LoginPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Sign-in failed");
      }
      storeAuthTokens(data);
      router.push("/");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sign-in failed");
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
          <span className="eyebrow">Welcome back</span>
          <h1>Sign in</h1>
          <p>Continue to your FinSight workspace.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required />
            </label>
            <label>
              Password
              <input name="password" type="password" autoComplete="current-password" required />
            </label>
            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </button>
            <p className="auth-message" role="alert">{message}</p>
          </form>
          <p className="auth-switch">New to FinSight? <a href="/register">Create an account</a></p>
        </div>
      </section>
    </main>
  );
}
