import 'dotenv/config'
import Fastify from 'fastify'
import cors from '@fastify/cors'
import { fastifyTRPCPlugin } from '@trpc/server/adapters/fastify'
import { appRouter } from './router'
import { verifyGraphArtifact } from './db'
import { env } from '@nutrition/config'

async function main() {
  const app = Fastify({ logger: false })
  await app.register(cors, { 
    origin: env.NODE_ENV === 'production' ? ['https://your.app'] : true 
  })

  // Fail fast if the compiled graph DB is missing/outdated.
  verifyGraphArtifact()

  await app.register(fastifyTRPCPlugin, {
    prefix: '/trpc',
    trpcOptions: { 
      router: appRouter,
      batching: { enabled: true }
    }
  })

  app.get('/', async () => ({ status: 'ok', service: 'nutrition-graph-api' }))

  await app.listen({ port: env.PORT, host: '0.0.0.0' })
  console.log(`[api] listening on http://localhost:${env.PORT}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
