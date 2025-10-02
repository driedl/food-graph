import { z } from 'zod'
import path from 'path'
import { PATHS } from './paths.js'

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().default(3000),
  DB_PATH: z.string().default(path.join(PATHS.workspaceRoot, 'apps/api/database/graph.dev.sqlite')),
  ETL_DB_PATH: z.string().default(PATHS.databaseAbsolute),
  MIN_GRAPH_SCHEMA_VERSION: z.coerce.number().default(5),
  AUTO_COPY_ETL_DB: z.enum(['true', 'false']).default('true'),
  // Database source toggle
  FOOD_DB_SOURCE: z.enum(['etl', 'mise']).default('etl'),
  FOOD_DB_PATH_ETL: z.string().default(PATHS.databaseAbsolute),
  FOOD_DB_PATH_MISE: z.string().default(PATHS.miseDatabaseAbsolute),
})

export const env = schema.parse(process.env)

export { PATHS, resolvePath, getAbsolutePaths } from './paths.js'