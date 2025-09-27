import { createTRPCReact } from '@trpc/react-query'
import type { AppRouter } from '../../../apps/api/src/router' // type-only import across workspace
export const trpc = createTRPCReact<AppRouter>()
