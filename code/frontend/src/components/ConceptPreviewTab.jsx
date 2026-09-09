import { useState } from 'react'
import FlowAnimation from './diagrams/FlowAnimation.jsx'
import ConceptFlashcards from './ConceptFlashcards.jsx'
import { CONCEPTS } from '../data/conceptPreview.js'

const STEP_SETS = {
  triggers: [
    { id: 'signal', label: 'Drift / performance / schedule signal', color: '#94a3b8' },
    { id: 'priority', label: 'Deduplicate by priority', color: '#0ea5e9' },
    { id: 'dag', label: 'Start the 16-stage DAG', color: '#6366f1' },
    { id: 'volume', label: 'Volume check', color: '#f59e0b' },
    { id: 'train', label: 'Train or BLOCK', color: '#059669' },
  ],
  gate: [
    { id: 'candidate', label: 'Candidate metrics', color: '#94a3b8' },
    { id: 'champion', label: 'Champion metrics', color: '#0ea5e9' },
    { id: 'thresholds', label: 'Minimum F1/precision/recall', color: '#6366f1' },
    { id: 'regression', label: 'Max regression check', color: '#f59e0b' },
    { id: 'decision', label: 'PASS or FAIL', color: '#059669' },
  ],
  regression: [
    { id: 'champion_f1', label: 'Champion F1', color: '#94a3b8' },
    { id: 'candidate_f1', label: 'Candidate F1', color: '#0ea5e9' },
    { id: 'diff', label: '(champion - candidate) / champion', color: '#6366f1' },
    { id: 'pct', label: 'Regression %', color: '#f59e0b' },
    { id: 'gate', label: 'Compare to 3% budget', color: '#059669' },
  ],
  canary: [
    { id: 'stage', label: 'Stage', color: '#94a3b8' },
    { id: 'smoke', label: 'Smoke test', color: '#0ea5e9' },
    { id: 'c5', label: 'Canary 5%', color: '#6366f1' },
    { id: 'c50', label: 'Canary 25% -> 50%', color: '#f59e0b' },
    { id: 'prod', label: 'Canary 100% -> Production', color: '#059669' },
  ],
  rollback: [
    { id: 'monitor', label: 'Monitor production', color: '#94a3b8' },
    { id: 'detect', label: 'Regression detected', color: '#f87171' },
    { id: 'stop', label: 'Stop promotion', color: '#f59e0b' },
    { id: 'restore', label: 'Restore previous champion', color: '#6366f1' },
    { id: 'alert', label: 'PagerDuty + audit log', color: '#059669' },
  ],
  lineage: [
    { id: 'run', label: 'Training run', color: '#94a3b8' },
    { id: 'params', label: 'Log params + metrics', color: '#0ea5e9' },
    { id: 'gate', label: 'Gate PASS?', color: '#f59e0b' },
    { id: 'register', label: 'Register model version', color: '#7c3aed' },
    { id: 'stage', label: 'Candidate -> Staging -> Production', color: '#059669' },
  ],
  sla: [
    { id: 'stage', label: 'Each DAG stage', color: '#94a3b8' },
    { id: 'duration', label: 'Measure duration', color: '#0ea5e9' },
    { id: 'threshold', label: 'Compare to max_minutes', color: '#f59e0b' },
    { id: 'violation', label: 'Log SLA violation', color: '#f87171' },
    { id: 'compliance', label: 'Fleet-wide compliance %', color: '#059669' },
  ],
}

export default function ConceptPreviewTab() {
  const [activeId, setActiveId] = useState(CONCEPTS[0].id)
  const active = CONCEPTS.find((c) => c.id === activeId) || CONCEPTS[0]

  return (
    <div className="grid concept-preview">
      <section className="card span-2 concept-preview-hero">
        <p className="eyebrow">Before you dive in</p>
        <h2>Concept preview — Drift-Aware Continuous Training Platform</h2>
        <p className="lead">
          Seven bite-sized illustrated concepts that explain how this platform decides whether — and when
          — to retrain a production model: what triggers a run, how the evaluation gate protects
          production, the exact regression math, canary deployment, automatic rollback, MLflow/Registry
          lineage, and pipeline SLA monitoring.
        </p>
      </section>

      <section className="card span-2 concept-preview-nav">
        <div className="concept-chip-row" role="tablist" aria-label="Concept topics">
          {CONCEPTS.map((concept) => (
            <button
              key={concept.id}
              type="button"
              role="tab"
              aria-selected={activeId === concept.id}
              className={activeId === concept.id ? 'concept-chip active' : 'concept-chip'}
              onClick={() => setActiveId(concept.id)}
            >
              {concept.title}
            </button>
          ))}
        </div>
      </section>

      {active && (
        <section className="card span-2 concept-preview-detail" key={active.id}>
          <header className="concept-preview-detail-head">
            <div>
              <span className="concept-preview-subtitle">{active.subtitle}</span>
              <h3>{active.title}</h3>
            </div>
          </header>

          <div className="concept-preview-illustration">
            <FlowAnimation steps={STEP_SETS[active.illustration] || STEP_SETS.gate} />
          </div>

          <p className="concept-preview-summary">{active.summary}</p>

          {active.flashcard?.takeaway && (
            <blockquote className="concept-pull-quote">
              <span className="concept-pull-label">Key takeaway</span>
              {active.flashcard.takeaway}
            </blockquote>
          )}

          {active.example && (
            <article className="concept-example-card">
              <h4>{active.example.title}</h4>
              <ol>
                {active.example.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </article>
          )}
        </section>
      )}

      <section className="card span-2 concept-flashdeck-section">
        <ConceptFlashcards concepts={CONCEPTS} activeId={activeId} onSelect={setActiveId} />
      </section>
    </div>
  )
}
