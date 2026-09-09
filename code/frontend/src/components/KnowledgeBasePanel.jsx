import AboutProjectTab from './AboutProjectTab.jsx'
import ConceptPreviewTab from './ConceptPreviewTab.jsx'
import ModelsAlgosTab from './ModelsAlgosTab.jsx'
import ArchitectureTab from './ArchitectureTab.jsx'
import CodeTab from './CodeTab.jsx'
import ToolsFrameworksTab from './ToolsFrameworksTab.jsx'
import GlossaryTab from './GlossaryTab.jsx'
import UnderstandingCheckTab from './UnderstandingCheckTab.jsx'

export default function KnowledgeBasePanel({ setError, section = 'about', setSection }) {
  const jumpTo = setSection || (() => {})

  return (
    <div className="kb-panel-only">
      {section === 'about' && <AboutProjectTab />}
      {section === 'concepts' && <ConceptPreviewTab setError={setError} />}
      {section === 'glossary' && <GlossaryTab />}
      {section === 'models' && <ModelsAlgosTab setError={setError} />}
      {section === 'architecture' && <ArchitectureTab setError={setError} />}
      {section === 'code' && <CodeTab setError={setError} />}
      {section === 'tools' && <ToolsFrameworksTab setError={setError} />}
      {section === 'check' && <UnderstandingCheckTab setError={setError} onJumpToSection={jumpTo} />}
    </div>
  )
}
