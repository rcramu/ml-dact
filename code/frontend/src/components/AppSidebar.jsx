import { MAIN_NAV, PLATFORM_NAV, KB_NAV } from '../data/navSections.js'

function NavButton({ item, active, onClick }) {
  return (
    <button
      type="button"
      className={active ? 'side-nav-item active' : 'side-nav-item'}
      onClick={() => onClick(item.id)}
    >
      <span className="side-nav-label">{item.label}</span>
      <span className="side-nav-desc">{item.description}</span>
    </button>
  )
}

export default function AppSidebar({ view, onNavigate }) {
  return (
    <aside className="app-sidebar card" aria-label="Main navigation">
      <section className="side-nav-group">
        <h2 className="side-nav-heading">Explore</h2>
        <p className="side-nav-intro muted">Trigger retraining, watch the DAG, review deployments &amp; alerts.</p>
        <nav className="side-nav-list">
          {MAIN_NAV.map((item) => (
            <NavButton key={item.id} item={item} active={view === item.id} onClick={onNavigate} />
          ))}
        </nav>
      </section>

      <section className="side-nav-group">
        <h2 className="side-nav-heading">Platform</h2>
        <nav className="side-nav-list">
          {PLATFORM_NAV.map((item) => (
            <NavButton key={item.id} item={item} active={view === item.id} onClick={onNavigate} />
          ))}
        </nav>
      </section>

      <section className="side-nav-group side-nav-kb">
        <h2 className="side-nav-heading">Knowledge Base</h2>
        <p className="side-nav-intro muted">Concepts, glossary, formulas, architecture &amp; a self-check quiz.</p>
        <nav className="side-nav-list">
          {KB_NAV.map((item) => (
            <NavButton key={item.id} item={item} active={view === item.id} onClick={onNavigate} />
          ))}
        </nav>
      </section>
    </aside>
  )
}
