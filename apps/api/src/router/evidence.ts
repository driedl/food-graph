import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'

export const evidenceRouter = t.router({
    summaryByTaxon: t.procedure
        .input(z.object({ taxonId: z.string() }))
        .query(({ input }) => {
            // Placeholder structure for future integration.
            // Keep the shape stable so the UI can render badges/empty states today.
            return {
                taxonId: input.taxonId,
                hasDirect: false,
                directCount: 0,
                rollupCount: 0,
                lastUpdated: null as string | null,
            }
        }),
})
