export const WORK_MODES = ["remote", "hybrid", "onsite"] as const
export type WorkMode = (typeof WORK_MODES)[number]
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

export interface JobSource {
  source: string
  url: string
  first_seen_at: string
}

// Jobs as listed: "new" means found by the latest ingestion run
export interface JobListItem extends Job {
  is_new: boolean
}

export interface JobDetail extends JobListItem {
  description: string | null
  captured_at: string | null
  sources: JobSource[]
}

export interface JobPasteInput {
  title: string
  company_name: string
  url: string
  description: string
  location: string | null
  employment_type: string | null
  work_mode: WorkMode | null
}

export const APPLICATION_STATUSES = [
  "interested",
  "not_interested",
  "applied",
  "interview",
  "rejected",
  "offer",
] as const

export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number]

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  interested: "Interested",
  not_interested: "Not interested",
  applied: "Applied",
  interview: "Interview",
  rejected: "Rejected",
  offer: "Offer",
}

export interface Application {
  id: number
  status: ApplicationStatus
  notes: string | null
  snapshot_id: number
  created_at: string
  updated_at: string
  job_posting: Job
}

export interface Profile {
  id: number
  full_name: string
  headline: string | null
  summary: string | null
  created_at: string
  updated_at: string
}

export interface ProfileInput {
  full_name: string
  headline: string | null
  summary: string | null
}