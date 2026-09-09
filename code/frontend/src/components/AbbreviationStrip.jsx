// Collapsed by default — user must click "Expand all" to reveal expansions.
import { useState } from 'react'
import { ABBREVIATIONS } from '../data/abbreviations.js'

export default function AbbreviationStrip() {
  const [expanded, setExpanded] = useState(false)

  return (
    <aside className={`abbr-strip ${expanded ? 'expanded' : ''}`} aria-label="Abbreviation expansions">
      <div className="abbr-strip-bar">
        <span className="abbr-strip-label">Abbreviations</span>
        <button
          type="button"
          className="abbr-strip-toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? 'Collapse' : 'Expand all'}
        </button>
      </div>

      <div className="abbr-strip-scroll">
        {ABBREVIATIONS.map(({ abbr, expansion }) => (
          <span key={abbr} className="abbr-chip" title={expansion}>
            <strong className="abbr-short">{abbr}</strong>
            <span className="abbr-arrow" aria-hidden="true">→</span>
            <span className="abbr-long">{expansion}</span>
          </span>
        ))}
      </div>
    </aside>
  )
}
