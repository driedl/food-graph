import 'dotenv/config'
import Fastify from 'fastify'
import cors from '@fastify/cors'
import { fastifyTRPCPlugin } from '@trpc/server/adapters/fastify'
import { appRouter } from './router'
import { migrate, seedMinimal, isEmpty } from './db'

const PORT = Number(process.env.PORT || 3000)

async function main() {
  const app = Fastify({ logger: false })
  await app.register(cors, { origin: true })

  migrate()
  if (isEmpty()) seedMinimal()

  await app.register(fastifyTRPCPlugin, {
    prefix: '/trpc',
    trpcOptions: { router: appRouter }
  })

  app.get('/', async () => ({ status: 'ok', service: 'nutrition-graph-api' }))

  await app.listen({ port: PORT, host: '0.0.0.0' })
  console.log(`[api] listening on http://localhost:${PORT}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
