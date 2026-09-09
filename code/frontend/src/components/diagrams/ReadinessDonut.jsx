import { useAnimationControl } from '../../context/AnimationContext.jsx'

/** Animated donut showing risk-severity distribution across all analyzed contracts. */
export default function ReadinessDonut({ segments, size = 180 }) {
  const { paused } = useAnimationControl()
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1
  const radius = size / 2 - 18
  const circumference = 2 * Math.PI * radius
  let offsetAcc = 0

  return (
    <svg
      className={`readiness-donut ${paused ? 'paused' : ''}`}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Risk distribution donut chart"
    >
      <g transform={`translate(${size / 2}, ${size / 2}) rotate(-90)`}>
        <circle r={radius} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="20" />
        {segments.map((seg, i) => {
          const frac = seg.value / total
          const dash = frac * circumference
          const circle = (
            <circle
              key={seg.label}
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth="20"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={-offsetAcc}
              className="donut-arc draw-arc"
              style={{ '--delay': `${i * 0.15}s` }}
              strokeLinecap="butt"
            />
          )
          offsetAcc += dash
          return circle
        })}
      </g>
      <text x="50%" y="46%" textAnchor="middle" className="donut-center-value">{Math.round(segments[0]?.value || 0)}%</text>
      <text x="50%" y="60%" textAnchor="middle" className="donut-center-label">{segments[0]?.label}</text>
    </svg>
  )
}
