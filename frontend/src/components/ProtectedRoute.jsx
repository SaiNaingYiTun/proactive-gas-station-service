import { Navigate, useLocation } from 'react-router'

import { isLoggedIn, isOwner } from '../lib/auth.js'

// Wraps a route element: sends a logged-out viewer to /login (remembering
// where they were headed, so login sends them back), and optionally
// restricts to the owner account specifically (staff management).
function ProtectedRoute({ children, ownerOnly = false }) {
  const location = useLocation()

  if (!isLoggedIn()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (ownerOnly && !isOwner()) {
    return <Navigate to="/" replace />
  }
  return children
}

export default ProtectedRoute
