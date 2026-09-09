import { useMemo, useState } from 'react'
import { GLOSSARY, GLOSSARY_TOPICS, glossaryTermsForTopic } from '../data/glossary.js'
import { TermExplain } from './TermExplain.jsx'

const FILTERS = [{ id: 'all', label: 'All terms' }, ...GLOSSARY_TOPICS.map(({ id, label }) => ({ id, label }))]

export default function GlossaryTab() {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')

  const visibleIds = useMemo(() => {
    const base = glossaryTermsForTopic(filter)
    const q = query.trim().toLowerCase()
    if (!q) return base
    return base.filter((id) => {
      const entry = GLOSSARY[id]
      const hay = `${id} ${entry.term} ${entry.definition} ${entry.inThisStack || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [query, filter])

  return (
    <div className="grid">
      <section className="card span-2 glossary-tab">
        <h2>Term glossary</h2>
        <p className="muted">Plain-language definitions for every modeling/legal-tech concept used on this platform — searchable by topic.</p>

        <div className="glossary-toolbar">
          <input
            type="search"
            className="glossary-search-input"
            placeholder="Search terms… e.g. TF-IDF, deviation, obligation"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search glossary"
          />
          <div className="glossary-filters" role="group" aria-label="Filter by topic">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={filter === item.id ? 'glossary-filter active' : 'glossary-filter'}
                onClick={() => setFilter(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <p className="muted glossary-count">
          {visibleIds.length} term{visibleIds.length === 1 ? '' : 's'}
          {query ? ` matching "${query}"` : ''}
        </p>

        {visibleIds.length === 0 ? (
          <p className="muted">No terms match your search.</p>
        ) : (
          <div className="glossary-grid">
            {visibleIds.map((id) => (
              <div key={id} className="glossary-result">
                <TermExplain id={id} compact />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
