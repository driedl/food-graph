import { z } from 'zod'
import { PATHS } from './paths.js'

const schema = z.object({
  NODE_ENV: z.enum(['development','test','production']).default('development'),
  PORT: z.coerce.number().default(3000),
  DB_PATH: z.string().default(PATHS.databaseAbsolute),
})

export const env = schema.parse(process.env)
export { PATHS, resolvePath, getAbsolutePaths } from './paths.js'