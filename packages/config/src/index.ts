import { z } from 'zod'
import path from 'path'
import { PATHS } from './paths.js'

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().default(3000),
  // API's own database location
  DB_PATH: z.string().default(path.join(PATHS.workspaceRoot, 'apps/api/database/graph.dev.sqlite')),
  AUTO_COPY_ETL_DB: z.enum(['true', 'false']).default('true'),
  // ETL2 source database location (the database the API should copy from)
  ETL2_DB_PATH: z.string().default(PATHS.databaseAbsolute),
})

export const env = schema.parse(process.env)

export { PATHS, resolvePath, getAbsolutePaths } from './paths.js'