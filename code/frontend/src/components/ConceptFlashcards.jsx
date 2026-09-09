import { useCallback, useEffect, useState } from 'react'

const CARD_ACCENTS = {
  availability_slo: '#6366f1',
  latency_percentiles: '#0ea5e9',
  error_budget: '#f59e0b',
  composite_health: '#059669',
  slice_evaluation: '#7c3aed',
  runtime_anomaly: '#f87171',
  mlflow_airflow_lineage: '#34d399',
}

function Flashcard({ concept, flipped, onFlip, onExplore, isActive }) {
  const fc = concept.flashcard || {}
  const accent = CARD_ACCENTS[concept.id] || '#6366f1'

  return (
    <div className={`flashcard-wrap ${isActive ? 'active' : ''}`}>
      <button
        type="button"
        className={`flashcard-scene ${flipped ? 'is-flipped' : ''}`}
        onClick={onFlip}
        aria-pressed={flipped}
        aria-label={`${concept.title} flashcard — ${flipped ? 'show question' : 'show answer'}`}
        style={{ '--flash-accent': accent }}
      >
        <span className="flashcard-inner">
          <span className="flashcard-face flashcard-front">
            <span className="flashcard-emoji" aria-hidden="true">{fc.emoji || '💡'}</span>
            <span className="flashcard-label">Question</span>
            <strong className="flashcard-title">{concept.title}</strong>
            <p className="flashcard-question">{fc.question || concept.subtitle}</p>
            <span className="flashcard-hint">Tap to reveal</span>
          </span>
          <span className="flashcard-face flashcard-back">
            <span className="flashcard-label">Answer</span>
            <p className="flashcard-takeaway">{fc.takeaway || concept.summary}</p>
            {fc.try_it && (
              <p className="flashcard-try">
                <span className="flashcard-try-label">Try it</span>
                {fc.try_it}
              </p>
            )}
            <span className="flashcard-hint">Tap to flip back</span>
          </span>
        </span>
      </button>
      {flipped && onExplore && (
        <button type="button" className="flashcard-explore-btn" onClick={onExplore}>
          Explore full lesson ↑
        </button>
      )}
    </div>
  )
}

export default function ConceptFlashcards({ concepts, activeId, onSelect }) {
  const [deckIndex, setDeckIndex] = useState(0)
  const [flippedIds, setFlippedIds] = useState(() => new Set())
  const [deckFlipped, setDeckFlipped] = useState(false)

  const activeIndex = concepts.findIndex((c) => c.id === activeId)
  useEffect(() => {
    if (activeIndex >= 0) setDeckIndex(activeIndex)
  }, [activeIndex])

  useEffect(() => {
    const concept = concepts[deckIndex]
    if (concept && concept.id !== activeId) onSelect?.(concept.id)
  }, [deckIndex])

  const current = concepts[deckIndex]
  const flippedCount = concepts.filter((c) => flippedIds.has(c.id)).length

  const toggleFlip = useCallback((id, solo = false) => {
    setFlippedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    if (solo) setDeckFlipped((f) => !f)
  }, [])

  const goPrev = useCallback(() => {
    setDeckFlipped(false)
    setDeckIndex((i) => (i - 1 + concepts.length) % concepts.length)
  }, [concepts.length])

  const goNext = useCallback(() => {
    setDeckFlipped(false)
    setDeckIndex((i) => (i + 1) % concepts.length)
  }, [concepts.length])

  const scrollToLesson = useCallback(() => {
    requestAnimationFrame(() => {
      document.querySelector('.concept-preview-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }, [])

  const exploreConcept = useCallback((concept) => {
    if (!concept) return
    onSelect?.(concept.id)
    setDeckIndex(concepts.indexOf(concept))
    setDeckFlipped(true)
    setFlippedIds((prev) => new Set(prev).add(concept.id))
    scrollToLesson()
  }, [concepts, onSelect, scrollToLesson])

  return (
    <section className="concept-flashdeck">
      <header className="flashdeck-header">
        <div>
          <h3>All concepts at a glance</h3>
          <p className="muted flashdeck-sub">Click a card to flip · use the arrows to browse the deck</p>
        </div>
        <div className="flashdeck-progress" aria-live="polite">
          <span className="flashdeck-counter">{deckIndex + 1} / {concepts.length}</span>
          <span className="flashdeck-studied">{flippedCount} revealed</span>
        </div>
      </header>

      <div className="flashdeck-stage">
        <button type="button" className="flashdeck-nav" onClick={goPrev} aria-label="Previous card">‹</button>
        <div className="flashdeck-main">
          {concepts.map((concept, i) => {
            const offset = i - deckIndex
            if (Math.abs(offset) > 2) return null
            const isCenter = i === deckIndex
            return (
              <div
                key={concept.id}
                className={`flashdeck-stack-card pos-${offset}`}
                style={{ zIndex: 10 - Math.abs(offset) }}
                aria-hidden={!isCenter}
              >
                {isCenter && current && (
                  <Flashcard
                    concept={current}
                    flipped={deckFlipped}
                    onFlip={() => toggleFlip(current.id, true)}
                    onExplore={() => exploreConcept(current)}
                    isActive
                  />
                )}
              </div>
            )
          })}
        </div>
        <button type="button" className="flashdeck-nav" onClick={goNext} aria-label="Next card">›</button>
      </div>

      <div className="flashdeck-dots" role="tablist" aria-label="Flashcard positions">
        {concepts.map((concept, i) => (
          <button
            key={concept.id}
            type="button"
            role="tab"
            aria-selected={i === deckIndex}
            className={`flashdeck-dot ${i === deckIndex ? 'active' : ''} ${flippedIds.has(concept.id) ? 'studied' : ''}`}
            onClick={() => { setDeckIndex(i); setDeckFlipped(false); onSelect?.(concept.id) }}
            title={concept.title}
          />
        ))}
      </div>

      <div className="flashdeck-gallery">
        <p className="flashdeck-gallery-label">Flip any mini card for a quick refresher</p>
        <div className="flashdeck-gallery-scroll">
          {concepts.map((concept) => (
            <Flashcard
              key={concept.id}
              concept={concept}
              flipped={flippedIds.has(concept.id)}
              onFlip={() => toggleFlip(concept.id)}
              onExplore={() => exploreConcept(concept)}
              isActive={concept.id === activeId}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
