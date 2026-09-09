import { useMemo, useState } from 'react'
import { QUIZ_DOC } from '../data/quiz.js'

function shuffleArray(items) {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export default function UnderstandingCheckTab({ onJumpToSection }) {
  const doc = QUIZ_DOC
  const [topicFilter, setTopicFilter] = useState('all')
  const [quizStarted, setQuizStarted] = useState(false)
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [answers, setAnswers] = useState([])

  const pool = useMemo(() => {
    if (topicFilter === 'all') return doc.questions
    return doc.questions.filter((q) => q.topic === topicFilter)
  }, [doc, topicFilter])

  const current = questions[index]
  const finished = quizStarted && index >= questions.length && questions.length > 0

  const score = useMemo(() => {
    if (!answers.length) return { correct: 0, total: 0, pct: 0 }
    const correct = answers.filter((a) => a.correct).length
    return { correct, total: answers.length, pct: Math.round((correct / answers.length) * 100) }
  }, [answers])

  const weakTopics = useMemo(() => {
    const misses = answers.filter((a) => !a.correct)
    return doc.topics.filter((t) => misses.some((m) => m.topic === t.id))
  }, [answers, doc])

  const startQuiz = (mode = 'all') => {
    const source = mode === 'quick' ? shuffleArray(pool).slice(0, Math.min(7, pool.length)) : shuffleArray(pool)
    setQuestions(source)
    setIndex(0)
    setSelected(null)
    setRevealed(false)
    setAnswers([])
    setQuizStarted(true)
  }

  const chooseOption = (optionIndex) => {
    if (revealed || !current) return
    setSelected(optionIndex)
    setRevealed(true)
    const correct = optionIndex === current.correct_index
    setAnswers((prev) => [...prev, { id: current.id, topic: current.topic, correct, chosen: optionIndex }])
  }

  const nextQuestion = () => {
    setSelected(null)
    setRevealed(false)
    setIndex((i) => i + 1)
  }

  const resetQuiz = () => {
    setQuizStarted(false)
    setQuestions([])
    setIndex(0)
    setSelected(null)
    setRevealed(false)
    setAnswers([])
  }

  const topicLabel = doc.topics.find((t) => t.id === current?.topic)?.label
  const passed = score.pct >= Math.round((doc.passing_score || 0.7) * 100)

  return (
    <div className="grid understanding-check">
      <section className="card span-2 uc-hero">
        <p className="eyebrow">Self-assessment</p>
        <h2>{doc.title}</h2>
        <p className="lead">{doc.summary}</p>
        <p className="muted uc-meta">
          {doc.questions.length} questions across {doc.topics.length} topics (≥7 each) · passing score {Math.round((doc.passing_score || 0.7) * 100)}%
        </p>
      </section>

      {!quizStarted && (
        <section className="card span-2 uc-setup">
          <h3>Choose a focus area</h3>
          <div className="uc-topic-filters">
            <button
              type="button"
              className={topicFilter === 'all' ? 'uc-topic active' : 'uc-topic'}
              onClick={() => setTopicFilter('all')}
            >
              All topics ({doc.questions.length})
            </button>
            {doc.topics.map((topic) => (
              <button
                key={topic.id}
                type="button"
                className={topicFilter === topic.id ? 'uc-topic active' : 'uc-topic'}
                onClick={() => setTopicFilter(topic.id)}
              >
                {topic.label} ({doc.questions.filter((q) => q.topic === topic.id).length})
              </button>
            ))}
          </div>

          <div className="uc-start-actions">
            <button type="button" className="primary-btn" onClick={() => startQuiz('all')} disabled={!pool.length}>
              Start full quiz ({pool.length})
            </button>
            <button type="button" className="ghost-btn" onClick={() => startQuiz('quick')} disabled={pool.length < 1}>
              Quick check (7 random)
            </button>
          </div>
        </section>
      )}

      {quizStarted && !finished && current && (
        <section className="card span-2 uc-question-card">
          <div className="uc-progress-head">
            <span className="uc-progress-label">
              Question {index + 1} of {questions.length}
              {topicLabel && <span className="uc-topic-tag">{topicLabel}</span>}
            </span>
            <div className="uc-progress-bar" aria-hidden="true">
              <div className="uc-progress-fill" style={{ width: `${((index + (revealed ? 1 : 0)) / questions.length) * 100}%` }} />
            </div>
          </div>

          <h3 className="uc-question-text">{current.question}</h3>

          <div className="uc-options" role="list">
            {current.options.map((option, i) => {
              let state = ''
              if (revealed) {
                if (i === current.correct_index) state = 'correct'
                else if (i === selected) state = 'wrong'
                else state = 'dim'
              } else if (i === selected) state = 'selected'

              return (
                <button
                  key={option}
                  type="button"
                  className={`uc-option ${state}`}
                  onClick={() => chooseOption(i)}
                  disabled={revealed}
                >
                  <span className="uc-option-letter">{String.fromCharCode(65 + i)}</span>
                  <span>{option}</span>
                </button>
              )
            })}
          </div>

          {revealed && (
            <div className={`uc-feedback ${selected === current.correct_index ? 'ok' : 'bad'}`}>
              <strong>{selected === current.correct_index ? 'Correct' : 'Not quite'}</strong>
              <p>{current.explanation}</p>
              {onJumpToSection && current.kb_section && selected !== current.correct_index && (
                <button type="button" className="ghost-btn" onClick={() => onJumpToSection(current.kb_section)}>
                  Review in Knowledge Base →
                </button>
              )}
              <button type="button" className="primary-btn uc-next-btn" onClick={nextQuestion}>
                {index + 1 >= questions.length ? 'See results' : 'Next question'}
              </button>
            </div>
          )}
        </section>
      )}

      {finished && (
        <section className="card span-2 uc-results">
          <h3>{passed ? 'Nice work!' : "Keep studying — you're getting there"}</h3>
          <div className={`uc-score-ring ${passed ? 'pass' : 'retry'}`}>
            <span className="uc-score-value">{score.pct}%</span>
            <span className="uc-score-detail">{score.correct} / {score.total} correct</span>
          </div>

          <div className="uc-topic-breakdown">
            <h4>By topic</h4>
            {doc.topics.map((topic) => {
              const topicAnswers = answers.filter((a) => a.topic === topic.id)
              if (!topicAnswers.length) return null
              const ok = topicAnswers.filter((a) => a.correct).length
              return (
                <div key={topic.id} className="uc-topic-row">
                  <span>{topic.label}</span>
                  <span>{ok}/{topicAnswers.length}</span>
                </div>
              )
            })}
          </div>

          {weakTopics.length > 0 && onJumpToSection && (
            <div className="uc-review-links">
              <h4>Review weak areas</h4>
              <div className="uc-review-btns">
                {weakTopics.map((topic) => {
                  const section = doc.questions.find((q) => q.topic === topic.id)?.kb_section || 'concepts'
                  return (
                    <button key={topic.id} type="button" className="ghost-btn" onClick={() => onJumpToSection(section)}>
                      {topic.label} →
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div className="uc-start-actions">
            <button type="button" className="primary-btn" onClick={() => startQuiz('all')}>Try again (full)</button>
            <button type="button" className="ghost-btn" onClick={resetQuiz}>Change topic</button>
          </div>
        </section>
      )}
    </div>
  )
}
