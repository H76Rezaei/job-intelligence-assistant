import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { apiGet, apiPatch, errorMessage } from "../api/client"
import {
  APPLICATION_STATUSES,
  STATUS_LABELS,
  type Application,
  type ApplicationStatus,
} from "../api/types"

function ApplicationsPage() {
  const [filter, setFilter] = useState<ApplicationStatus | "">("")
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    // "cancelled" ignores a slow response that arrives after the filter changed again
    let cancelled = false
    apiGet<Application[]>("/applications", filter ? { status: filter } : undefined)
      .then((data) => {
        if (cancelled) return
        setApplications(data)
        setError(null)
      })
      .catch((e) => {
        if (!cancelled) setError(errorMessage(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [filter])

  async function changeStatus(application: Application, status: ApplicationStatus) {
    setActionError(null)
    try {
      const updated = await apiPatch<Application>(`/applications/${application.id}`, { status })
      setApplications((list) =>
        filter && updated.status !== filter
          ? list.filter((a) => a.id !== updated.id) // no longer matches the filter
          : list.map((a) => (a.id === updated.id ? updated : a)),
      )
    } catch (e) {
      setActionError(errorMessage(e))
    }
  }

  if (loading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">Could not load applications: {error}</p>

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-xl font-semibold">Applications</h2>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as ApplicationStatus | "")}
          className="rounded border px-2 py-1 text-sm"
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {APPLICATION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>
      {actionError && <p className="mb-2 text-sm text-red-600">{actionError}</p>}

      {applications.length === 0 ? (
        <p className="text-gray-600">
          {filter
            ? "No applications with this status."
            : "No applications yet. Mark a job as interested on its detail page."}
        </p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="border-b font-semibold">
            <tr>
              <th className="py-2">Job</th>
              <th>Company</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((a) => (
              <tr key={a.id} className="border-b">
                <td className="py-2">
                  <Link to={`/jobs/${a.job_posting.id}`} className="text-blue-600 hover:underline">
                    {a.job_posting.title}
                  </Link>
                </td>
                <td>{a.job_posting.company.name}</td>
                <td>
                  <select
                    value={a.status}
                    onChange={(e) => changeStatus(a, e.target.value as ApplicationStatus)}
                    className="rounded border px-2 py-1"
                    aria-label={`Status of ${a.job_posting.title}`}
                  >
                    {APPLICATION_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="max-w-xs truncate text-gray-600">{a.notes || "-"}</td>
                <td className="text-gray-600">
                  {new Date(a.updated_at).toLocaleDateString("de-DE")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default ApplicationsPage