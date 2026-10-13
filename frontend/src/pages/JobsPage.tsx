import { useEffect, useState } from "react"
import { apiGet } from "../api/client"
import type { Job } from "../api/types"

function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet<Job[]>("/jobs")
      .then(setJobs)
      .catch((e) => setError(e.message))
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
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((job) => (
          <tr key={job.id} className="border-b">
            <td className="py-2">{job.title}</td>
            <td>{job.company.name}</td>
            <td>{job.location ?? "-"}</td>
            <td>{job.work_mode ?? "-"}</td>
            <td>
              <a href={job.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                Open
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default JobsPage