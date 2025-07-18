import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/common/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { ExperimentPage } from '@/pages/ExperimentPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ConfigurationPage } from '@/pages/ConfigurationPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/experiment" element={<ExperimentPage />} />
        <Route path="/experiment/:id" element={<ExperimentPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/configuration" element={<ConfigurationPage />} />
      </Routes>
    </Layout>
  )
}

export default App 