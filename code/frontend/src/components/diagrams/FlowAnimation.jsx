import { useAnimationControl } from '../../context/AnimationContext.jsx'

/** Generic animated pipeline of pulsing nodes connected by dashed lines. */
export default function FlowAnimation({ steps, caption }) {
  const { paused } = useAnimationControl()
  return (
    <div className={`transformer-flow ${paused ? 'paused' : ''}`} aria-hidden="true">
      <div className="flow-track">
        {steps.map((step, i) => (
          <div key={step.id} className="flow-node-wrap">
            <div className="flow-node pulse" style={{ '--node-color': step.color, '--delay': `${i * 0.35}s` }}>
              {step.label}
            </div>
            {i < steps.length - 1 && <div className="flow-connector animate-dash" />}
          </div>
        ))}
      </div>
      {caption && <p className="flow-caption muted">{caption}</p>}
    </div>
  )
}
