import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { trpc } from './lib/trpc'
import { httpBatchLink } from '@trpc/client'
import App from './App'
import './index.css'

const client = new QueryClient()
const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({ url: '/trpc' }),
  ],
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <trpc.Provider client={trpcClient} queryClient={client}>
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    </trpc.Provider>
  </React.StrictMode>,
)
