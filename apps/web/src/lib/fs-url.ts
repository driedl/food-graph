// Build a FS URL path from an fs string like "fs:/a/b/c/part:x/tx:y{a=1}"
export function fsToPath(fs: string) {
  const clean = fs.replace(/^fs:\/*/, '')
  const encoded = clean.split('/').map(encodeURIComponent).join('/')
  return '/workbench/fs/' + encoded
}

// Try to extract an FS string from the current location. Returns null if not FS form.
export function pathToFs(pathname: string): string | null {
  const m = pathname.match(/^\/workbench\/fs\/(.+)$/)
  if (!m) return null
  const decoded = m[1].split('/').map(decodeURIComponent).join('/')
  return 'fs:/' + decoded
}

// Extract taxon id from /workbench/node/:id
export function pathToNodeId(pathname: string): string | null {
  const m = pathname.match(/^\/workbench\/node\/([^/]+)\/?$/)
  return m ? m[1] : null
}
