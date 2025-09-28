import { createTRPCReact } from '@trpc/react-query'
import type { AppRouter } from '@nutrition/api-contract'
export const trpc = createTRPCReact<AppRouter>()
