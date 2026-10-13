import axios from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
})

export async function apiGet<T>(path: string): Promise<T> {
  const response = await api.get<T>(path)
  return response.data
}