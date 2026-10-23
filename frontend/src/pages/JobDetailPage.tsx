import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { apiGet, errorMessage, httpStatus } from "../api/client"
import type { Application, JobDetail } from "../api/types"
import ApplicationControls from "../components/ApplicationControls"

const SOURCE_LABELS: Record<string, string> = {
  paste: "Added by me",
  bundesagentur: "Bundesagentur",
}

function JobDetailPage() {
  const { id } = useParams()
  const [job, setJob] = useState<JobDetail | null>(null)
  const [application, setApplication] = useState<Application | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // The API has no "application for this job" lookup, so we fetch the list and match
    Promise.all([
      apiGet<JobDetail>(`/jobs/${id}`),
      apiGet<Application[]>("/applications"),
    ])
      .then(([jobData, applications]) => {
        setJob(jobData)
        setApplication(applications.find((a) => a.job_posting.id === jobData.id) ?? null)
      })
      .catch((e) => setError(httpStatus(e) === 404 ? "Job not found" : errorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p>Loading...</p>
  if (error || !job) return <p className="text-red-600">{error ?? "Job not found"}</p>

  return (
    <div className="max-w-3xl">
      <Link to="/jobs" className="text-sm text-blue-600 hover:underline">
        Back to jobs
      </Link>
      <h2 className="mt-4 text-xl font-semibold">{job.title}</h2>
      <p className="text-gray-600">
        {job.company.name} · {job.location ?? "Location not given"} ·{" "}
        {job.work_mode ?? "Work mode not given"}
      </p>
      <p className="text-sm text-gray-600">
        Found on:{" "}
        {job.sources.length === 0 ? (
          <a href={job.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
            original posting
          </a>
        ) : (
          job.sources.map((s, i) => (
            <span key={s.url}>
              {i > 0 && ", "}
              <a href={s.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                {SOURCE_LABELS[s.source] ?? s.source}
              </a>
            </span>
          ))
        )}
      </p>

      <ApplicationControls jobId={job.id} application={application} onChange={setApplication} />

      <h3 className="mt-6 font-semibold">Description</h3>
      {job.description ? (
        <p className="mt-2 whitespace-pre-wrap">{job.description}</p>
      ) : (
        <p className="mt-2 text-gray-600">No snapshot text stored for this job.</p>
      )}
    </div>
  )
}

export default JobDetailPage