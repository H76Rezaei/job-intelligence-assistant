import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { apiPost, errorMessage } from "../api/client"
import { WORK_MODES, type JobDetail, type JobPasteInput, type WorkMode } from "../api/types"

const inputClass = "mt-1 w-full rounded border px-3 py-2 text-sm"

const EMPTY_FORM = {
  title: "",
  company_name: "",
  url: "",
  description: "",
  location: "",
  employment_type: "",
  work_mode: "",
}

function PasteJobPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function field(name: keyof typeof EMPTY_FORM) {
    return {
      id: name,
      value: form[name],
      onChange: (e: { target: { value: string } }) => setForm({ ...form, [name]: e.target.value }),
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    const body: JobPasteInput = {
      title: form.title.trim(),
      company_name: form.company_name.trim(),
      url: form.url.trim(),
      description: form.description.trim(),
      location: form.location.trim() || null,
      employment_type: form.employment_type.trim() || null,
      work_mode: (form.work_mode || null) as WorkMode | null,
    }
    try {
      // The API answers with the existing job when this one is already known
      const job = await apiPost<JobDetail>("/jobs", body)
      navigate(`/jobs/${job.id}`)
    } catch (e) {
      setError(errorMessage(e))
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="max-w-2xl space-y-4">
      <Link to="/jobs" className="text-sm text-blue-600 hover:underline">
        Back to jobs
      </Link>
      <h2 className="text-xl font-semibold">Add a job</h2>
      <p className="text-sm text-gray-600">
        Paste a job you found yourself. If it is already in the list, it is attached to that job.
      </p>

      <div>
        <label htmlFor="title" className="text-sm font-medium">Title</label>
        <input required maxLength={255} className={inputClass} {...field("title")} />
      </div>
      <div>
        <label htmlFor="company_name" className="text-sm font-medium">Company</label>
        <input required maxLength={255} className={inputClass} {...field("company_name")} />
      </div>
      <div>
        <label htmlFor="url" className="text-sm font-medium">Link to the posting</label>
        <input required type="url" maxLength={2048} className={inputClass} {...field("url")} />
      </div>
      <div>
        <label htmlFor="description" className="text-sm font-medium">Full posting text</label>
        <textarea required rows={14} className={inputClass} {...field("description")} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label htmlFor="location" className="text-sm font-medium">Location (optional)</label>
          <input maxLength={255} className={inputClass} {...field("location")} />
        </div>
        <div>
          <label htmlFor="employment_type" className="text-sm font-medium">
            Employment type (optional)
          </label>
          <input
            maxLength={50}
            placeholder="e.g. full-time"
            className={inputClass}
            {...field("employment_type")}
          />
        </div>
        <div>
          <label htmlFor="work_mode" className="text-sm font-medium">Work mode (optional)</label>
          <select className={inputClass} {...field("work_mode")}>
            <option value="">Not given</option>
            {WORK_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {mode[0].toUpperCase() + mode.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">Could not save: {error}</p>}
      <button
        type="submit"
        disabled={saving}
        className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save job"}
      </button>
    </form>
  )
}

export default PasteJobPage
