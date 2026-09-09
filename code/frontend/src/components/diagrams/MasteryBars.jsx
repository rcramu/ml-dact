/** Animated horizontal bar list — used for risk-type/model-metric visualizations. */
export default function MasteryBars({ rows, valueKey = 'value', labelKey = 'label' }) {
  return (
    <div className="mastery-bars">
      {rows.map((row, i) => {
        const pct = Math.round((row[valueKey] || 0) * 100)
        const tone = pct >= 70 ? 'high' : pct >= 45 ? 'mid' : 'low'
        return (
          <div key={row[labelKey]} className="mastery-bar-row">
            <span className="mastery-bar-label">{row[labelKey]}</span>
            <div className="mastery-bar-track">
              <div
                className={`mastery-bar-fill ${tone} grow-bar`}
                style={{ '--target-width': `${pct}%`, '--delay': `${i * 0.06}s` }}
              />
            </div>
            <span className="mastery-bar-value">{pct}%</span>
          </div>
        )
      })}
    </div>
  )
}
