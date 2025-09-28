#!/usr/bin/env tsx
import { appRouter } from '../apps/api/src/router'

function walk(prefix: string, r: any) {
  for (const [k, v] of Object.entries<any>(r._def?.record ?? {})) {
    if (v._def?.router) walk(`${prefix}${k}.`, v)
    else console.log(`${prefix}${k}`)
  }
}

console.log('TRPC Routes:')
walk('', appRouter)
