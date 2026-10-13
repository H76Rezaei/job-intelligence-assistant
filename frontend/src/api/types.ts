export type WorkMode = "remote" | "onsite" | "hybrid"
export type JobStatus = "open" | "closed"

export interface Company {
  id: number
  name: string
  domain: string | null
  industry: string | null
  careers_url: string | null
  created_at: string
  updated_at: string
}

export interface Job {
  id: number
  title: string
  location: string | null
  employment_type: string | null
  work_mode: WorkMode | null
  url: string
  status: JobStatus
  first_seen_at: string
  last_seen_at: string
  company: Company
}