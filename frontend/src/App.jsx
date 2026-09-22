import { Routes, Route } from 'react-router'

import AppLayout from './layouts/AppLayout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'

import Login from './pages/Login.jsx'
import Overview from './pages/Overview.jsx'
import Vehicles from './pages/Vehicles.jsx'
import Analytics from './pages/Analytics.jsx'
import Settings from './pages/Settings.jsx'
import StaffManagement from './pages/StaffManagement.jsx'

function App() {
  return (
    <Routes>

      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Overview />
            </AppLayout>
          </ProtectedRoute>
        }
      />


      <Route
        path="/vehicles"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Vehicles />
            </AppLayout>
          </ProtectedRoute>
        }
      />


      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Analytics />
            </AppLayout>
          </ProtectedRoute>
        }
      />


      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Settings />
            </AppLayout>
          </ProtectedRoute>
        }
      />


      <Route
        path="/staff"
        element={
          <ProtectedRoute ownerOnly>
            <AppLayout>
              <StaffManagement />
            </AppLayout>
          </ProtectedRoute>
        }
      />

    </Routes>
  )
}

export default App
