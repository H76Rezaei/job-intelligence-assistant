import { useState } from "react"
import { apiPatch, apiPost, errorMessage } from "../api/client"
import {
  APPLICATION_STATUSES,
  STATUS_LABELS,
  type Application,
  type ApplicationStatus,
} from "../api/types"

interface Props {
  jobId: number
  application: Application | null
  onChange: (application: Application) => void
}

function ApplicationControls({ jobId, application, onChange }: Props) {
  const [notes, setNotes] = useState(application?.notes ?? "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run(request: Promise<Application>) {
    setBusy(true)
    setError(null)
    try {
      onChange(await request)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  function setStatus(status: ApplicationStatus) {
    if (application?.status === status) return
    if (application) {
      run(apiPatch<Application>(`/applications/${application.id}`, { status }))
    } else {
      run(apiPost<Application>("/applications", { job_posting_id: jobId, status }))
    }
  }

  function saveNotes() {
    if (!application) return
    // PATCH ignores null, so an empty string is how notes get cleared
    run(apiPatch<Application>(`/applications/${application.id}`, { notes }))
  }

  return (
    <section className="mt-6 rounded border p-4">
      <h3 className="font-semibold">My status</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        {APPLICATION_STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            disabled={busy}
            onClick={() => setStatus(status)}
            className={`rounded border px-3 py-1 text-sm disabled:opacity-50 ${
              application?.status === status
                ? "border-blue-600 bg-blue-600 text-white"
                : "hover:bg-gray-100"
            }`}
          >
            {STATUS_LABELS[status]}
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {application ? (
        <div className="mt-4">
          <label className="text-sm font-medium" htmlFor="notes">
            Notes
          </label>
          <textarea
            id="notes"
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
          />
          <button
            type="button"
            disabled={busy || notes === (application.notes ?? "")}
            onClick={saveNotes}
            className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            Save notes
          </button>
        </div>
      ) : (
        <p className="mt-3 text-sm text-gray-600">
          Pick a status to start tracking this job. Notes become available afterwards.
        </p>
      )}
    </section>
  )
}

export default ApplicationControls