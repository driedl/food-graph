import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { routeTree } from './routeTree.gen'
import { trpc } from './lib/trpc'
import { httpBatchLink } from '@trpc/client'
import './index.css'
import './styles/theme.css'

const client = new QueryClient({
  defaultOptions: { 
    queries: { 
      refetchOnWindowFocus: false, 
      staleTime: 30_000 
    } 
  }
})
const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({ url: '/trpc' }),
  ],
})

const router = createRouter({ 
  routeTree,
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
})

if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
}

// Add router event listeners for debugging
router.subscribe('onLoad', (e) => {
})

router.subscribe('onBeforeLoad', (e) => {
})

// Note: onError is not available in current TanStack Router version
// router.subscribe('onError', (e) => {
//   console.error('Router error:', e)
// })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

// App component that includes devtools
const App = () => {
  return (
    <>
      <RouterProvider router={router} />
      {import.meta.env.DEV && (
        <TanStackRouterDevtools 
          router={router}
          position="bottom-right" 
        />
      )}
    </>
  )
}

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <trpc.Provider client={trpcClient} queryClient={client}>
        <QueryClientProvider client={client}>
          <App />
        </QueryClientProvider>
      </trpc.Provider>
    </React.StrictMode>,
  )
} catch (error) {
  console.error('Error rendering app:', error)
  document.getElementById('root')!.innerHTML = `<div style="padding: 20px; color: red;">Error: ${error}</div>`
}
