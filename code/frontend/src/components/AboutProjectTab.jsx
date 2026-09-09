import FlowAnimation from './diagrams/FlowAnimation.jsx'
import { stackConfig } from '../config.js'

const DEMO_STEPS = [
  { id: 'trigger', label: 'Trigger', color: '#6366f1' },
  { id: 'train', label: 'Train (PyTorch)', color: '#ee4c2c' },
  { id: 'evaluate', label: 'Evaluate vs. champion', color: '#f59e0b' },
  { id: 'gate', label: 'Gate: promote / reject', color: '#7c3aed' },
  { id: 'deploy', label: 'Canary -> production', color: '#059669' },
]

const MAIN_TABS = [
  { id: 'training', title: 'Training Runs', desc: 'Trigger retraining, watch the 16-stage DAG live, browse full history' },
  { id: 'models', title: 'Models & Registry', desc: 'Champion vs. challenger comparison, version lineage, MLflow Registry' },
  { id: 'deployment', title: 'Deployment & Rollback', desc: 'Canary rollout stages, automatic/manual rollback, SLA compliance' },
  { id: 'alerts', title: 'Alerts', desc: 'Slack/PagerDuty-style notifications across the whole pipeline' },
  { id: 'ingested-data', title: 'Ingested Data', desc: 'Seeded datasets, raw training records, quality checks, audit trail' },
]

const KB_SECTIONS = [
  { title: 'About this Project', desc: 'Goals and scope' },
  { title: 'Concept Preview', desc: 'Illustrated concepts + flashcards' },
  { title: 'Term Glossary', desc: 'Searchable definitions' },
  { title: 'Formulas & Algorithms', desc: 'Evaluation gate math, PyTorch model, SLA formulas' },
  { title: 'Architecture', desc: 'Full DAG + roadmap' },
  { title: 'Explain the Code', desc: 'Repo layout and pipeline/rollback flows' },
  { title: 'Tools & Frameworks', desc: 'FastAPI, PyTorch, MLflow, Airflow, PostgreSQL, React' },
  { title: 'Check My Understanding', desc: 'Self-check quiz (7+ questions per topic)' },
]

export default function AboutProjectTab() {
  return (
    <div className="grid about-project">
      <section className="card span-2 about-hero">
        <p className="eyebrow">MLOps &middot; Drift Detection &middot; Continuous Training (reference implementation)</p>
        <h2>About this project &mdash; Drift-Aware Continuous Training Platform</h2>
        <p className="lead">
          This platform is the reference implementation for the paper <em>"A Production-Grade
          Closed-Loop MLOps Architecture for Drift-Aware Continuous Training and Deployment Using
          Airflow, MLflow, PyTorch, and Kubernetes."</em> It automates the closed loop <strong>monitor -&gt;
          detect drift -&gt; retrain -&gt; evaluate -&gt; quality-gate -&gt; deploy -&gt; monitor</strong> for a
          customer-churn classifier. Retraining is triggered by statistical drift (PSI/KS), performance
          degradation, a schedule, data availability, or a manual request; a real PyTorch model is trained
          on a seeded synthetic churn dataset; every run is tracked in MLflow; a multi-dimensional quality
          gate (paper Section 9) compares the challenger against the current production champion; only a
          passing candidate is canary-deployed to production &mdash; and an automatic rollback restores the
          previous champion the moment a regression is detected.
        </p>
        <div className="about-pills">
          <span className="about-pill">PSI / KS drift detection</span>
          <span className="about-pill">Drift/performance/schedule triggers</span>
          <span className="about-pill">16-stage DAG</span>
          <span className="about-pill">Real PyTorch training</span>
          <span className="about-pill">MLflow tracking + Registry</span>
          <span className="about-pill">Multi-dimensional quality gate</span>
          <span className="about-pill">Canary deployment</span>
          <span className="about-pill">Automatic rollback</span>
          <span className="about-pill">SLA monitoring</span>
          <span className="about-pill">Apache Airflow</span>
          <span className="about-pill">FastAPI &middot; Swagger</span>
        </div>
        <FlowAnimation steps={DEMO_STEPS} caption="Monitor -> detect drift -> train -> evaluate -> gate -> canary deploy" />
      </section>

      <section className="card">
        <h3>Scope of this reference implementation</h3>
        <ul className="compact-list">
          <li>Every one of the paper's Section 7.2 experiment conditions actually runs at startup: healthy baseline (Experiment 1), a blocked data-volume anomaly, drift-triggered promotion (Experiments 2 &amp; 3), a data-quality-warning rejection, and a regression rejection</li>
          <li>One real rollback is seeded too, so Deployment &amp; Rollback has real history to browse from the first request</li>
          <li>A single flagship model, <code>churn-predictor</code>, exercises the full closed loop against the synthetic customer-churn dataset described in Section 7.1</li>
          <li>AWS EKS, GPU training, and real Slack/PagerDuty delivery are documented in the Knowledge Base as a roadmap, not run here &mdash; Docker Compose is the practical local substitute for EKS</li>
        </ul>
      </section>

      <section className="card">
        <h3>Main menu</h3>
        <ul className="about-tab-list">
          {MAIN_TABS.map((t) => (
            <li key={t.id}><strong>{t.title}</strong> — {t.desc}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Knowledge Base</h3>
        <ul className="about-tab-list">
          {KB_SECTIONS.map((t) => (
            <li key={t.title}><strong>{t.title}</strong> — {t.desc}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Stack URLs</h3>
        <ul className="compact-list">
          <li>UI: <a href={stackConfig.uiUrl} target="_blank" rel="noreferrer">localhost:{stackConfig.uiPort}</a></li>
          <li>API / Swagger: <a href={`${stackConfig.apiUrl}/docs`} target="_blank" rel="noreferrer">localhost:{stackConfig.apiPort}/docs</a></li>
          <li>MLflow: <a href={stackConfig.mlflowUrl} target="_blank" rel="noreferrer">localhost:{stackConfig.mlflowPort}</a></li>
          <li>Airflow: <a href={stackConfig.airflowUrl} target="_blank" rel="noreferrer">localhost:{stackConfig.airflowPort}</a> (admin/admin)</li>
        </ul>
      </section>
    </div>
  )
}
