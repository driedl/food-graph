// Build a FS URL path from an fs string like "fs:/a/b/c/part:x/tx:y{a=1}"
export function fsToPath(fs: string) {
  const clean = fs.replace(/^fs:\/*/, '')
  return '/workbench/fs/' + clean
}

// Try to extract an FS string from the current location. Returns null if not FS form.
export function pathToFs(pathname: string): string | null {
  const m = pathname.match(/^\/workbench\/fs\/(.+)$/)
  if (!m) return null
  return 'fs:/' + m[1]
}

// Extract taxon id from /workbench/node/:id
export function pathToNodeId(pathname: string): string | null {
  const m = pathname.match(/^\/workbench\/node\/([^/]+)\/?$/)
  return m ? m[1] : null
}
