import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import { stackConfig } from './config.js'
import { StatusDot } from './components/shared.jsx'
import AppSidebar from './components/AppSidebar.jsx'
import DriftMonitoringTab from './components/DriftMonitoringTab.jsx'
import TrainingTab from './components/TrainingTab.jsx'
import ModelsRegistryTab from './components/ModelsRegistryTab.jsx'
import DeploymentTab from './components/DeploymentTab.jsx'
import AlertsTab from './components/AlertsTab.jsx'
import IngestedDataTab from './components/IngestedDataTab.jsx'
import ApiReferenceTab from './components/ApiReferenceTab.jsx'
import KnowledgeBasePanel from './components/KnowledgeBasePanel.jsx'
import AbbreviationStrip from './components/AbbreviationStrip.jsx'
import { AnimationProvider, useAnimationControl } from './context/AnimationContext.jsx'
import { MAIN_NAV, PLATFORM_NAV, KB_NAV, isKbView, kbSectionFromView } from './data/navSections.js'

const VIEW_TITLES = Object.fromEntries([
  ...MAIN_NAV.map((n) => [n.id, n.label]),
  ...PLATFORM_NAV.map((n) => [n.id, n.label]),
  ...KB_NAV.map((n) => [n.id, n.label]),
])

function AppShell() {
  const [view, setView] = useState('drift')
  const [kbSection, setKbSection] = useState('about')
  const [selectedModel, setSelectedModel] = useState(null)
  const [ready, setReady] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { paused, setPaused } = useAnimationControl()

  const refresh = useCallback(async () => {
    setError('')
    try {
      setReady(await api.ready())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const onSidebarNavigate = useCallback((id) => {
    setView(id)
    if (isKbView(id)) setKbSection(kbSectionFromView(id))
  }, [])

  const openModel = useCallback((modelName, targetView = 'models') => {
    setSelectedModel(modelName)
    setView(targetView)
  }, [])

  const panelTitle = VIEW_TITLES[view] || 'Drift-Aware Continuous Training Platform'

  function renderMain() {
    if (view === 'drift') return <DriftMonitoringTab setError={setError} selectedModel={selectedModel} setSelectedModel={setSelectedModel} />
    if (view === 'training') return <TrainingTab setError={setError} selectedModel={selectedModel} setSelectedModel={setSelectedModel} onOpenModel={openModel} />
    if (view === 'models') return <ModelsRegistryTab setError={setError} selectedModel={selectedModel} setSelectedModel={setSelectedModel} onOpenModel={openModel} />
    if (view === 'deployment') return <DeploymentTab setError={setError} selectedModel={selectedModel} setSelectedModel={setSelectedModel} />
    if (view === 'alerts') return <AlertsTab setError={setError} />
    if (view === 'ingested-data') return <IngestedDataTab setError={setError} />
    if (view === 'api-reference') return <ApiReferenceTab setError={setError} />
    if (isKbView(view)) {
      return <KnowledgeBasePanel setError={setError} section={kbSection} setSection={setKbSection} />
    }
    return <TrainingTab setError={setError} selectedModel={selectedModel} setSelectedModel={setSelectedModel} onOpenModel={openModel} />
  }

  return (
    <div className="app app-with-sidebar">
      <header className="hero">
        <div>
          <p className="eyebrow">Closed-Loop MLOps Reference Implementation &middot; PyTorch + MLflow + Airflow</p>
          <h1>Drift-Aware Continuous Training Platform</h1>
          <p className="subtitle">Drift detection (PSI/KS) &middot; drift/performance/schedule-triggered retraining &middot; quality gate &middot; canary deployment &middot; automatic rollback</p>
        </div>
        <div className="hero-status">
          {ready && (
            <>
              <StatusDot ok={ready.database} label="Database" />
              <StatusDot ok={ready.models_seeded > 0} label="Models seeded" />
              <StatusDot ok={ready.pipeline_runs_seeded > 0} label="Runs seeded" />
              <StatusDot ok={ready.ready} label="Ready" />
            </>
          )}
        </div>
      </header>

      <div className="app-toolbar">
        <span className="panel-title">{panelTitle}</span>
        <label className="tab ghost pause-toggle toolbar-action">
          <input type="checkbox" checked={paused} onChange={(e) => setPaused(e.target.checked)} />
          Pause animations
        </label>
        <button type="button" className="tab ghost refresh toolbar-action" onClick={refresh}>Refresh</button>
      </div>

      {error && <div className="alert">{error}</div>}

      {loading ? (
        <p className="muted">Connecting to API…</p>
      ) : (
        <div className="app-body">
          <AppSidebar view={view} onNavigate={onSidebarNavigate} />
          <main className="app-main">{renderMain()}</main>
        </div>
      )}

      <footer className="foot">
        Swagger: <a href={`${stackConfig.apiUrl}/docs`} target="_blank" rel="noreferrer">/docs</a>
        {' · '}
        <a href={`${stackConfig.apiUrl}/redoc`} target="_blank" rel="noreferrer">ReDoc</a>
        {' · '}
        MLflow: <a href={stackConfig.mlflowUrl} target="_blank" rel="noreferrer">:{stackConfig.mlflowPort}</a>
        {' · '}
        Airflow: <a href={stackConfig.airflowUrl} target="_blank" rel="noreferrer">:{stackConfig.airflowPort}</a> (admin/admin)
      </footer>
      <AbbreviationStrip />
    </div>
  )
}

export default function App() {
  return (
    <AnimationProvider>
      <AppShell />
    </AnimationProvider>
  )
}

