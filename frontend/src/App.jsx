import { Routes, Route } from 'react-router'

import AppLayout from './layouts/AppLayout.jsx'

import Overview from './pages/Overview.jsx'
import LiveDetection from './pages/LiveDetection.jsx'
import Vehicles from './pages/Vehicles.jsx'
import Analytics from './pages/Analytics.jsx'
import Settings from './pages/Settings.jsx'

function App() {
  return (
    <Routes>

      <Route
        path="/"
        element={
          <AppLayout>
            <Overview />
          </AppLayout>
        }
      />


      <Route
        path="/live-detection"
        element={
          <AppLayout>
            <LiveDetection />
          </AppLayout>
        }
      />


      <Route
        path="/vehicles"
        element={
          <AppLayout>
            <Vehicles />
          </AppLayout>
        }
      />


      <Route
        path="/analytics"
        element={
          <AppLayout>
            <Analytics />
          </AppLayout>
        }
      />


      <Route
        path="/settings"
        element={
          <AppLayout>
            <Settings />
          </AppLayout>
        }
      />

    </Routes>
  )
}

export default App