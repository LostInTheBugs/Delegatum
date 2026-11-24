import { useEffect, useState } from 'react'

/** Version locale (synchronisée avec le footer / les releases). */
const LOCAL_VERSION = '2026.11.005'

function cmpVersions(a: string, b: string): number {
  const clean = (v: string) => v.replace(/^v/, '')
  // Compare the numeric part (before the first hyphen) first
  const numA = clean(a).split('-')[0]
  const numB = clean(b).split('-')[0]
  const segsA = numA.split('.').map(Number)
  const segsB = numB.split('.').map(Number)
  for (let i = 0; i < Math.max(segsA.length, segsB.length); i++) {
    const x = segsA[i] || 0
    const y = segsB[i] || 0
    if (x !== y) return x - y
  }
  // Numeric parts equal → compare pre-release suffixes
  const sufA = clean(a).includes('-') ? clean(a).slice(clean(a).indexOf('-')) : ''
  const sufB = clean(b).includes('-') ? clean(b).slice(clean(b).indexOf('-')) : ''
  if (sufA && !sufB) return 1   // a has suffix, b doesn't → a is newer
  if (!sufA && sufB) return -1  // b has suffix, a doesn't → b is newer
  if (sufA && sufB) {
    // Same base, compare -cN suffixes numerically
    const m1 = sufA.match(/^-(\w+)(\d+)$/)
    const m2 = sufB.match(/^-(\w+)(\d+)$/)
    if (m1 && m2) {
      if (m1[1] !== m2[1]) return m1[1].localeCompare(m2[1])
      return Number(m1[2]) - Number(m2[2])
    }
    return sufA.localeCompare(sufB)
  }
  return 0
}

/**
 * Bandeau « nouvelle version disponible » — le SEUL lien avec GitHub.
 * Interroge l'API publique des releases (aucun token) et compare avec la
 * version locale. Silencieux si à jour, si offline ou si l'API échoue.
 */
export default function VersionCheck() {
  const [latest, setLatest] = useState<string | undefined>(undefined)
  const [url, setUrl] = useState<string | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    fetch('https://api.github.com/repos/LostInTheBugs/Delegatum/releases/latest')
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (cancelled || !data?.tag_name) return
        if (cmpVersions(data.tag_name, LOCAL_VERSION) > 0) {
          setLatest(data.tag_name)
          setUrl(data.html_url || `https://github.com/LostInTheBugs/Delegatum/releases/tag/${data.tag_name}`)
        }
      })
      .catch(() => { /* offline ou API bloquée : silencieux */ })
    return () => { cancelled = true }
  }, [])

  if (!latest) return null

  return (
    <div style={{
      background: '#2b6cb0', color: '#fff', textAlign: 'center',
      padding: '8px 16px', fontSize: '.85rem', fontWeight: 600,
    }}>
      🚀 Une nouvelle version <strong>{latest}</strong> de Delegatum est disponible —{' '}
      <a href={url} target="_blank" rel="noreferrer" style={{ color: '#fff', textDecoration: 'underline' }}>
        voir les nouveautés
      </a>
    </div>
  )
}