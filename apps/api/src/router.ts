import { initTRPC } from '@trpc/server'
import { z } from 'zod'
import { db } from './db'

const t = initTRPC.create()

export const appRouter = t.router({
  health: t.procedure.query(() => ({ ok: true })),

  taxonomy: t.router({
    getRoot: t.procedure.query(() => {
      const root = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE parent_id IS NULL LIMIT 1').get()
      return root ?? null
    }),

    getChildren: t.procedure.input(z.object({ id: z.string() })).query(({ input }) => {
      const stmt = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE parent_id = ? ORDER BY name')
      return stmt.all(input.id)
    }),

    getNode: t.procedure.input(z.object({ id: z.string() })).query(({ input }) => {
      const stmt = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE id = ?')
      const node = stmt.get(input.id)
      return node ?? null
    }),

    pathToRoot: t.procedure.input(z.object({ id: z.string() })).query(({ input }) => {
      const out: any[] = []
      let current = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE id = ?').get(input.id)
      while (current) {
        out.push(current)
        if (!current.parentId) break
        current = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE id = ?').get(current.parentId)
      }
      return out.reverse()
    }),

    search: t.procedure.input(z.object({ q: z.string().min(1) })).query(({ input }) => {
      const q = `%${input.q.toLowerCase()}%`
      const stmt = db.prepare(`
        SELECT DISTINCT n.id, n.name, n.slug, n.rank, n.parent_id as parentId 
        FROM nodes n 
        LEFT JOIN synonyms s ON n.id = s.node_id 
        WHERE LOWER(n.name) LIKE ? OR LOWER(n.slug) LIKE ? OR LOWER(s.synonym) LIKE ?
        ORDER BY n.rank, n.name 
        LIMIT 50
      `)
      return stmt.all(q, q, q)
    }),
  }),
})

export type AppRouter = typeof appRouter
