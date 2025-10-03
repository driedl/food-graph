import { t } from './_t'
import { taxonomyRouter } from './taxonomy'
import { searchRouter } from './search'
import { entitiesRouter } from './entities'
import { browseRouter } from './browse'
import { taxaRouter } from './taxa'
import { tpRouter } from './tp'
import { tptRouter } from './tpt'
import { tptAdvancedRouter } from './tptAdvanced'
import { facetsRouter } from './facets'
import { docsRouter } from './docs'
import { foodstateRouter } from './foodstate'
import { evidenceRouter } from './evidence'

export const appRouter = t.router({
    health: t.procedure.query(() => ({ ok: true })),
    taxonomy: taxonomyRouter,
    search: searchRouter,
    entities: entitiesRouter,
    browse: browseRouter,
    taxa: taxaRouter,
    tp: tpRouter,
    tpt: tptRouter,
    tptAdvanced: tptAdvancedRouter,
    facets: facetsRouter,
    docs: docsRouter,
    foodstate: foodstateRouter,
    evidence: evidenceRouter,
})

export type AppRouter = typeof appRouter
