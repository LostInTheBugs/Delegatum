import { useState } from 'react'
import { useT } from '../i18n/I18nContext'
import { parseDossier, verifyDossier, type VerifyResult } from '../lib/registerIntegrity'

/**
 * Page PUBLIQUE de vérification d'un dossier d'intégrité du registre
 * sécurité/santé (art. L.414-14) — aucun compte requis.
 *
 * L'utilisateur dépose le fichier « registre_securite_integrite_*.json »
 * exporté depuis Delegatum ; tout le calcul SHA-256 se fait dans le
 * navigateur, rien n'est envoyé au serveur.
 */
export default function VerifyRegister() {
  const { t } = useT()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [fileName, setFileName] = useState('')

  async function handleFile(f: File | null) {
    if (!f) return
    setBusy(true)
    setError(null)
    setResult(null)
    setFileName(f.name)
    try {
      const text = await f.text()
      const dossier = parseDossier(text)
      setResult(await verifyDossier(dossier))
    } catch (e: any) {
      const msg = String(e?.message ?? '')
      if (msg === 'bad_file') setError(t('verify.bad_file'))
      else if (msg.toLowerCase().includes('crypto')) setError(t('verify.no_crypto'))
      else setError(msg || t('verify.bad_file'))
    } finally {
      setBusy(false)
    }
  }

  const check = (ok: boolean) => (ok ? '✅' : '❌')

  return (
    <div style={{ minHeight: '100vh', padding: '32px 16px 60px', background: 'var(--gray-100, #f5f6f8)' }}>
      <div style={{ maxWidth: 780, margin: '0 auto' }}>
        <h1 style={{ fontSize: '1.4rem', marginBottom: 4 }}>🔍 {t('verify.title')}</h1>
        <p style={{ fontSize: '.85rem', color: 'var(--gray-600)', marginTop: 0 }}>{t('verify.subtitle')}</p>

        <div className="card" style={{ padding: 16, marginBottom: 16 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start' }}>
            <span style={{ fontSize: '.85rem', fontWeight: 600 }}>{t('verify.choose')}</span>
            <input
              type="file"
              accept=".json,application/json"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
              style={{ fontSize: '.8rem' }}
            />
          </label>
          {fileName && <p style={{ fontSize: '.75rem', color: 'var(--gray-600)', marginBottom: 0 }}>{fileName}</p>}
          {busy && <div className="spinner" style={{ marginTop: 10 }} />}
          {error && <div className="error-msg" style={{ marginTop: 10 }}>{error}</div>}
        </div>

        {result && (
          <div className="card" style={{ padding: 16, marginBottom: 16 }}>
            <p style={{
              fontSize: '1rem', fontWeight: 700, marginTop: 0,
              color: result.ok ? 'var(--green, #1e7d32)' : 'var(--red, #c62828)',
            }}>
              {result.ok ? `✅ ${t('verify.ok')}` : `⚠️ ${t('verify.fail')}`}
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0', fontSize: '.85rem', lineHeight: 1.9 }}>
              <li>{check(result.chainOk)} {t('verify.chain')}
                {!result.chainOk && result.firstBrokenIndex !== null && (
                  <span style={{ color: 'var(--red, #c62828)' }}> — {t('verify.first_broken')} : {result.firstBrokenIndex + 1}</span>
                )}
              </li>
              <li>{check(result.projectionOk)} {t('verify.projection')}
                {!result.projectionOk && (
                  <span style={{ color: 'var(--red, #c62828)' }}> — {t('verify.mismatches')} :
                    {result.mismatches.slice(0, 5).map((m, i) => (
                      <span key={i}> <code>#{m.entry_id}/{m.field}</code></span>
                    ))}
                    {result.mismatches.length > 5 && <span> … (+{result.mismatches.length - 5})</span>}
                  </span>
                )}
              </li>
              <li>{check(result.sealsOk)} {t('verify.seals')} ({result.sealsChecked})
                {!result.sealsOk && (
                  <span style={{ color: 'var(--red, #c62828)' }}> — #{result.brokenSeals.join(', #')}</span>
                )}
              </li>
            </ul>
            <div style={{ fontSize: '.8rem', color: 'var(--gray-600)' }}>
              <div>{t('verify.events')} : <strong>{result.eventCount}</strong>{result.orgName ? ` · ${result.orgName}` : ''}{result.generatedAt ? ` · ${result.generatedAt.slice(0, 16).replace('T', ' ')}` : ''}</div>
              <div style={{ marginTop: 4 }}>
                {t('verify.head')} : <code style={{ fontSize: '.72rem', wordBreak: 'break-all' }}>{result.headHash ?? '—'}</code>
              </div>
            </div>
          </div>
        )}

        <div className="card" style={{ padding: 16 }}>
          <h2 style={{ fontSize: '.95rem', marginTop: 0 }}>{t('verify.howto_title')}</h2>
          <p style={{ fontSize: '.8rem', color: 'var(--gray-600)', marginBottom: 0 }}>{t('verify.howto')}</p>
        </div>

        <p style={{ marginTop: 18 }}>
          <a href="/" style={{ color: 'var(--blue, #1565c0)', fontSize: '.85rem', textDecoration: 'none' }}>{t('verify.back')}</a>
        </p>
      </div>
    </div>
  )
}
