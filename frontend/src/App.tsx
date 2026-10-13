import { useEffect, useState } from "react"
import { apiGet } from "./api/client"

function App() {
  const [status, setStatus] = useState("loading...")

  useEffect(() => {
    apiGet<{ status: string }>("/health")
      .then((data) => setStatus(data.status))
      .catch((error) => setStatus(error.message))
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Job Intelligence</h1>
      <p className="mt-2 text-gray-600">API status: {status}</p>
    </div>
  )
}

export default App