import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { apiGet, errorMessage } from "../api/client"
import type { Application, ApplicationStatus, JobListItem } from "../api/types"
import StatusBadge from "../components/StatusBadge"

function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([])
  const [onlyNew, setOnlyNew] = useState(false)
  const [statuses, setStatuses] = useState<Map<number, ApplicationStatus>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function toggleOnlyNew(checked: boolean) {
    setOnlyNew(checked)
    setLoading(true)
    setError(null)
  }

  useEffect(() => {
    const params = onlyNew ? { new_in_last_run: "true" } : undefined
    Promise.all([
      apiGet<JobListItem[]>("/jobs", params),
      apiGet<Application[]>("/applications"),
    ])
      .then(([jobList, applications]) => {
        setJobs(jobList)
        setStatuses(new Map(applications.map((a) => [a.job_posting.id, a.status])))
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [onlyNew])

  if (loading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">Could not load jobs: {error}</p>

  const addJob = (
    <Link
      to="/jobs/new"
      className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
    >
      Add job
    </Link>
  )

  const toolbar = (
    <div className="flex items-center justify-between">
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={onlyNew} onChange={(e) => toggleOnlyNew(e.target.checked)} />
        New in last run
      </label>
      {addJob}
    </div>
  )

  if (jobs.length === 0) {
    return (
      <div className="space-y-4">
        {toolbar}
        <p className="text-gray-600">
          {onlyNew
            ? "The last ingestion run found no new jobs."
            : "No jobs yet. Add one you found yourself, or run ingestion."}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {toolbar}
      <table className="w-full text-left text-sm">
        <thead className="border-b font-semibold">
          <tr>
            <th className="py-2">Title</th>
            <th>Company</th>
            <th>Location</th>
            <th>Work mode</th>
            <th>My status</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const status = statuses.get(job.id)
            return (
              <tr key={job.id} className="border-b">
                <td className="py-2">
                  <Link to={`/jobs/${job.id}`} className="text-blue-600 hover:underline">
                    {job.title}
                  </Link>
                  {job.is_new && (
                    <span className="ml-2 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-800">
                      new
                    </span>
                  )}
                </td>
                <td>{job.company.name}</td>
                <td>{job.location ?? "-"}</td>
                <td>{job.work_mode ?? "-"}</td>
                <td>{status ? <StatusBadge status={status} /> : "-"}</td>
                <td>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Open
                  </a>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default JobsPage