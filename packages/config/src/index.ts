import { z } from 'zod'
import path from 'node:path'

const Env = z.object({
  PORT: z.coerce.number().default(3000),
  // Always resolve relative to project root (where package.json with pnpm workspace is located)
  DB_PATH: z.string().default(path.resolve(process.cwd(), 'data', 'builds', 'graph.dev.sqlite')),
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
})

export type Env = z.infer<typeof Env>
export const env: Env = Env.parse(process.env)
