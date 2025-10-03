import { initTRPC, TRPCError } from '@trpc/server'

export const t = initTRPC.create()

export const nullToNotFound = t.middleware(async ({ next }) => {
    const res = await next()
    if (res.ok && res.data === null) {
        throw new TRPCError({ code: 'NOT_FOUND' })
    }
    return res
})
