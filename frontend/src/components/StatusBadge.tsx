import { STATUS_LABELS, type ApplicationStatus } from "../api/types"

const COLORS: Record<ApplicationStatus, string> = {
  interested: "bg-blue-100 text-blue-800",
  not_interested: "bg-gray-100 text-gray-600",
  applied: "bg-amber-100 text-amber-800",
  interview: "bg-purple-100 text-purple-800",
  rejected: "bg-red-100 text-red-800",
  offer: "bg-green-100 text-green-800",
}

function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

export default StatusBadge