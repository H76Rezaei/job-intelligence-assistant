import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'   // add


// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
