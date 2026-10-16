import axios, { isAxiosError } from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
})

export async function apiGet<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const response = await api.get<T>(path, { params })
  return response.data
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await api.post<T>(path, body)
  return response.data
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await api.patch<T>(path, body)
  return response.data
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await api.put<T>(path, body)
  return response.data
}

// HTTP status of a failed request, or undefined for network errors
export function httpStatus(error: unknown): number | undefined {
  return isAxiosError(error) ? error.response?.status : undefined
}

// FastAPI sends {"detail": "..."} for errors we raise ourselves
export function errorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (error.response) return `Request failed (${error.response.status})`
    return error.message
  }
  return error instanceof Error ? error.message : "Unknown error"
}