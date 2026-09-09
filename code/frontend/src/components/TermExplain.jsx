import { GLOSSARY } from '../data/glossary.js'

export function TermExplain({ id, compact = false }) {
  const entry = GLOSSARY[id]
  if (!entry) return null

  return (
    <aside className={`term-explain ${compact ? 'compact' : ''}`} aria-label={`Definition: ${entry.term}`}>
      <p className="term-name">{entry.term}</p>
      <p className="term-def">{entry.definition}</p>
      {entry.inThisStack && (
        <p className="term-stack">
          <span className="term-stack-label">In this stack</span>
          {entry.inThisStack}
        </p>
      )}
    </aside>
  )
}
