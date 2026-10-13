import { NavLink, Navigate, Route, Routes } from "react-router-dom"
import ApplicationsPage from "./pages/ApplicationsPage"
import JobsPage from "./pages/JobsPage"
import ProfilePage from "./pages/ProfilePage"

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "font-semibold text-blue-600" : "text-gray-600 hover:text-gray-900"

function App() {
  return (
    <div>
      <nav className="flex gap-6 border-b px-6 py-3">
        <span className="font-bold">Job Intelligence</span>
        <NavLink to="/jobs" className={linkClass}>Jobs</NavLink>
        <NavLink to="/applications" className={linkClass}>Applications</NavLink>
        <NavLink to="/profile" className={linkClass}>Profile</NavLink>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/jobs" replace />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App