import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { apiGet, errorMessage, httpStatus } from "../api/client"
import type { Application, JobDetail } from "../api/types"
import ApplicationControls from "../components/ApplicationControls"

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
      <a
        href={job.url}
        target="_blank"
        rel="noreferrer"
        className="text-sm text-blue-600 hover:underline"
      >
        Original posting
      </a>

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