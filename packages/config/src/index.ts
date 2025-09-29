import { z } from 'zod'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const schema = z.object({
  NODE_ENV: z.enum(['development','test','production']).default('development'),
  PORT: z.coerce.number().default(3000),
  DB_PATH: z.string().default(() => {
    // default to repo-root/data/builds/graph.dev.sqlite
    const __dirname = path.dirname(fileURLToPath(import.meta.url))
    const repoRoot = path.resolve(__dirname, '..', '..', '..')
    return path.join(repoRoot, 'data', 'builds', 'graph.dev.sqlite')
  }),
})

export const env = schema.parse(process.env)