export default function HomePage() {
  return (
    <main className="page-shell">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="FinSight home">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span>FinSight</span>
        </a>
        <span className="status"><span /> Local workspace</span>
      </nav>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <span className="eyebrow">Your money, clearly understood</span>
          <h1 id="hero-title">See the story behind every expense.</h1>
          <p>
            FinSight will bring transactions, budgets, recurring costs, and
            plain-language insights together in one calm workspace.
          </p>
          <div className="actions">
            <a className="primary-action" href="/dashboard">
              View dashboard
              <span aria-hidden="true">-&gt;</span>
            </a>
            <a className="secondary-action" href="/register">
              Create account
            </a>
            <a className="secondary-action" href="/import">
              Import a CSV
            </a>
            <a className="secondary-action" href="#project-overview">
              See what FinSight can do
            </a>
          </div>
        </div>

        <div className="preview" aria-label="FinSight dashboard preview">
          <div className="preview-header">
            <div>
              <span className="preview-label">Monthly overview</span>
              <strong>$5,420.00</strong>
            </div>
            <span className="period">November</span>
          </div>
          <div className="chart" aria-hidden="true">
            {[42, 68, 52, 78, 61, 88, 72, 94, 66, 82, 58, 76].map((height, index) => (
              <span key={index} style={{ height: `${height}%` }} />
            ))}
          </div>
          <div className="preview-footer">
            <div>
              <span className="preview-label">Income</span>
              <strong>$8,200</strong>
            </div>
            <div>
              <span className="preview-label">Spent</span>
              <strong>$2,780</strong>
            </div>
            <div>
              <span className="preview-label">Saved</span>
              <strong>$5,420</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="project-overview" className="capabilities" aria-label="Planned product areas">
        <article>
          <span className="capability-number">01</span>
          <h2>Bring everything in</h2>
          <p>Turn CSV exports and statements into clean, consistent transactions.</p>
        </article>
        <article>
          <span className="capability-number">02</span>
          <h2>Understand patterns</h2>
          <p>Spot spending trends, recurring costs, and changes over time.</p>
        </article>
        <article>
          <span className="capability-number">03</span>
          <h2>Ask in plain language</h2>
          <p>Get answers based on your own authorized financial information.</p>
        </article>
      </section>
    </main>
  );
}
