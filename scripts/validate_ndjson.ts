#!/usr/bin/env -S node --no-warnings
import fs from 'node:fs'
import path from 'node:path'

const files = process.argv.slice(2)
if (!files.length) {
  console.error('Usage: tsx scripts/validate_ndjson.ts <file1.jsonl> [file2.jsonl ...]')
  process.exit(1)
}

let ok = true
for (const fp of files) {
  const buf = fs.readFileSync(fp)
  const txt = buf.toString('utf8')
  // Verify LF endings
  if (txt.includes('\r\n')) {
    console.error(`[CRLF] ${fp} contains CRLF line endings`)
    ok = false
  }
  if (txt.includes('/n{') || txt.includes('}/n')) {
    console.error(`[slash-n] ${fp} appears to have literal "/n" artifacts`)
    ok = false
  }
  const lines = txt.split('\n').filter(Boolean)
  lines.forEach((line, i) => {
    try {
      const obj = JSON.parse(line)
      for (const k of ['id','display_name']) {
        if (!(k in obj)) throw new Error(`missing key: ${k}`)
      }
      if (!('parent' in obj)) {
        console.warn(`[warn] ${path.basename(fp)}:${i+1} missing "parent" (root?)`)
      }
    } catch (e) {
      console.error(`[JSON error] ${fp}:${i+1} ${String(e)}`)
      ok = false
    }
  })
  console.log(`[ok] ${fp} lines:`, lines.length)
}
process.exit(ok ? 0 : 2)
