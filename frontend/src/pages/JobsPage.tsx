import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { apiGet, errorMessage } from "../api/client"
import type { Application, ApplicationStatus, Job } from "../api/types"
import StatusBadge from "../components/StatusBadge"

function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [statuses, setStatuses] = useState<Map<number, ApplicationStatus>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([apiGet<Job[]>("/jobs"), apiGet<Application[]>("/applications")])
      .then(([jobList, applications]) => {
        setJobs(jobList)
        setStatuses(new Map(applications.map((a) => [a.job_posting.id, a.status])))
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">Could not load jobs: {error}</p>
  if (jobs.length === 0) {
    return <p className="text-gray-600">No jobs yet. They will appear once ingestion exists.</p>
  }

  return (
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
  )
}

export default JobsPage