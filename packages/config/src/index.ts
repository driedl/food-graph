import { z } from 'zod'
import { PATHS } from './paths.js'

const schema = z.object({
  NODE_ENV: z.enum(['development','test','production']).default('development'),
  PORT: z.coerce.number().default(3000),
  DB_PATH: z.string().default(PATHS.databaseAbsolute),
  ETL_DB_PATH: z.string().default('./dist/database/graph.dev.sqlite'),
  MIN_GRAPH_SCHEMA_VERSION: z.coerce.number().default(5),
  AUTO_COPY_ETL_DB: z.enum(['true','false']).default('true'),
})

export const env = schema.parse(process.env)
export { PATHS, resolvePath, getAbsolutePaths } from './paths.js'