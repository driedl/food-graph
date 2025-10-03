import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'
import { composeFoodState } from '../lib/foodstate'

export const foodstateRouter = t.router({
    compose: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            transforms: z.array(z.object({
                id: z.string(),
                params: z.record(z.any()).optional()
            })).default([])
        }))
        .query(({ input }) => {
            const res = composeFoodState(db as any, input)
            return res
        }),

    parse: t.procedure
        .input(z.object({ fs: z.string().min(1) }))
        .query(({ input }) => {
            // naive parser: fs:/a/b/c/part:.../tf:x{a=1}/tf:y
            const segs = input.fs.replace(/^fs:\/*/, '').split('/').filter(Boolean)
            const partIdx = segs.findIndex(s => s.startsWith('part:'))
            const taxonPath = partIdx >= 0 ? segs.slice(0, partIdx) : segs
            const part = partIdx >= 0 ? segs[partIdx] : null
            const txSegs = partIdx >= 0 ? segs.slice(partIdx + 1) : []

            const parseTx = (s: string) => {
                const m = s.match(/^([^{}]+)(?:\{(.+)\})?$/)
                if (!m) return { id: s, params: {} }
                const id = m[1]; const params: any = {}
                if (m[2]) {
                    for (const kv of m[2].split(',')) {
                        const [k, raw] = kv.split('=')
                        if (!k) continue
                        if (raw === 'true' || raw === 'false') params[k] = raw === 'true'
                        else if (!Number.isNaN(Number(raw))) params[k] = Number(raw)
                        else params[k] = raw
                    }
                }
                return { id, params }
            }

            return {
                taxonPath,
                partId: part,
                transforms: txSegs.map(parseTx),
            }
        }),
})
