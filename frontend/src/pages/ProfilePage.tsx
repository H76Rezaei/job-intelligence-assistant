import { useEffect, useState, type FormEvent } from "react"
import { apiGet, apiPut, errorMessage, httpStatus } from "../api/client"
import type { Profile, ProfileInput } from "../api/types"

const inputClass = "mt-1 w-full rounded border px-3 py-2 text-sm"

function ProfilePage() {
  const [form, setForm] = useState({ full_name: "", headline: "", summary: "" })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    apiGet<Profile>("/profile")
      .then((p) =>
        setForm({ full_name: p.full_name, headline: p.headline ?? "", summary: p.summary ?? "" }),
      )
      .catch((e) => {
        // 404 only means no profile exists yet, so the empty form is the right state
        if (httpStatus(e) !== 404) setError(errorMessage(e))
      })
      .finally(() => setLoading(false))
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    const body: ProfileInput = {
      full_name: form.full_name.trim(),
      headline: form.headline.trim() || null,
      summary: form.summary.trim() || null,
    }
    try {
      await apiPut<Profile>("/profile", body)
      setMessage("Saved")
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p>Loading...</p>

  return (
    <form onSubmit={save} className="max-w-2xl space-y-4">
      <h2 className="text-xl font-semibold">Profile</h2>
      <div>
        <label htmlFor="full_name" className="text-sm font-medium">
          Full name
        </label>
        <input
          id="full_name"
          required
          maxLength={255}
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="headline" className="text-sm font-medium">
          Headline
        </label>
        <input
          id="headline"
          maxLength={255}
          value={form.headline}
          onChange={(e) => setForm({ ...form, headline: e.target.value })}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="summary" className="text-sm font-medium">
          Summary
        </label>
        <textarea
          id="summary"
          rows={6}
          value={form.summary}
          onChange={(e) => setForm({ ...form, summary: e.target.value })}
          className={inputClass}
        />
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save profile"}
        </button>
        {message && <span className="text-sm text-green-700">{message}</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </form>
  )
}

export default ProfilePage