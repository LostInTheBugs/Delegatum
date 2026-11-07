import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useT } from '../i18n/I18nContext'
import NavBar from '../components/NavBar'
import * as api from '../api/client'

const INTERVALS = [
  { value: 0, labelKey: 'updates.interval_never' },
  { value: 1, labelKey: 'updates.interval_1h' },
  { value: 6, labelKey: 'updates.interval_6h' },
  { value: 12, labelKey: 'updates.interval_12h' },
  { value: 24, labelKey: 'updates.interval_24h' },
  { value: 168, labelKey: 'updates.interval_1week' },
]

function formatDate(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString()
}

export default function UpdatesPage() {
  const { t } = useT()
  const navigate = useNavigate()
  const [state, setState] = useState<api.UpdateStateResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [applying, setApplying] = useState(false)
  const [checkLoading, setCheckLoading] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)

  // ── Access guard ──
  useEffect(() => {
    api.getUpdateAllowed().then(res => {
      if (!res.allowed) navigate('/dashboard')
    }).catch(() => navigate('/dashboard'))
  }, [navigate])

  const fetchState = useCallback(async () => {
    try {
      const data = await api.getUpdateState()
      setState(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Initial fetch ──
  useEffect(() => {
    fetchState()
  }, [fetchState])

  // ── Polling while update is pending ──
  useEffect(() => {
    const pending = state && (state.request !== null || state.applier.running)
    if (!pending) return
    const id = setInterval(fetchState, 15000)
    return () => clearInterval(id)
  }, [state, fetchState])

  const handleCheck = async () => {
    setCheckLoading(true)
    setSaveError(null)
    try {
      await api.checkUpdate()
      await fetchState()
    } catch (err: any) {
      setSaveError(err.message || t('updates.error'))
    } finally {
      setCheckLoading(false)
    }
  }

  const handleSaveSettings = async () => {
    if (!state) return
    setSaving(true)
    setSaveError(null)
    try {
      await api.saveUpdateSettings({
        upd_check_h: state.settings.upd_check_h,
        upd_apply_auto: state.settings.upd_apply_auto,
      })
      await fetchState()
    } catch (err: any) {
      setSaveError(err.message || t('updates.error'))
    } finally {
      setSaving(false)
    }
  }

  const handleApply = async () => {
    if (!state || !window.confirm(t('updates.apply_confirm'))) return
    setApplying(true)
    setApplyError(null)
    try {
      await api.applyUpdate()
      await fetchState()
    } catch (err: any) {
      setApplyError(err.message || t('updates.error'))
    } finally {
      setApplying(false)
    }
  }

  if (loading) return (
    <>
      <NavBar />
      <main style={{ maxWidth: 720, margin: '0 auto', padding: 24 }}>{t('updates.loading')}</main>
    </>
  )

  if (!state) return (
    <>
      <NavBar />
      <main style={{ maxWidth: 720, margin: '0 auto', padding: 24 }}>{t('updates.error')}</main>
    </>
  )

  return (
    <>
      <NavBar />
      <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'sans-serif' }}>
        <h1>{t('updates.title')}</h1>

        {/* ── Version info ── */}
        <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <h2 style={{ marginTop: 0 }}>{t('updates.version_info')}</h2>
          <p><strong>{t('updates.installed_version')}</strong> {state.current}</p>
          <p><strong>{t('updates.latest_version')}</strong> {state.latest.version}</p>
          {state.available ? (
            <span style={{ display: 'inline-block', background: '#fff3cd', color: '#856404', padding: '4px 12px', borderRadius: 4, fontWeight: 600 }}>
              {t('updates.update_available')}
            </span>
          ) : (
            <span style={{ display: 'inline-block', background: '#d4edda', color: '#155724', padding: '4px 12px', borderRadius: 4, fontWeight: 600 }}>
              {t('updates.up_to_date')}
            </span>
          )}
        </section>

        {/* ── Version notes ── */}
        {state.latest.body && (
          <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16, marginBottom: 24 }}>
            <h2 style={{ marginTop: 0 }}>{t('updates.release_notes')}</h2>
            {state.latest.url && (
              <p><a href={state.latest.url} target="_blank" rel="noreferrer">{state.latest.url}</a></p>
            )}
            <pre style={{ whiteSpace: 'pre-wrap', background: '#f8f9fa', padding: 12, borderRadius: 4, overflowX: 'auto' }}>
              {state.latest.body}
            </pre>
            <p style={{ fontSize: '.85rem', color: '#6c757d' }}>
              {t('updates.published_on')} {formatDate(state.latest.published_at)}
            </p>
          </section>
        )}

        {/* ── Manual check ── */}
        <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <h2 style={{ marginTop: 0 }}>{t('updates.check_title')}</h2>
          <p>
            <strong>{t('updates.last_check')}</strong> {formatDate(state.check.last_at)}
          </p>
          {state.check.error && (
            <p style={{ color: '#dc3545' }}><strong>{t('updates.check_error')}</strong> {state.check.error}</p>
          )}
          <button onClick={handleCheck} disabled={checkLoading} style={{
            background: checkLoading ? '#6c757d' : 'var(--blue)',
            color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600,
          }}>
            {checkLoading ? t('updates.checking') : t('updates.check_now')}
          </button>
          {saveError && <p style={{ color: '#dc3545', marginTop: 8 }}>{saveError}</p>}
        </section>

        {/* ── Apply ── */}
        {state.available && state.request === null && !state.applier.running && (
          <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16, marginBottom: 24 }}>
            <h2 style={{ marginTop: 0 }}>{t('updates.apply_title')}</h2>
            <button onClick={handleApply} disabled={applying} style={{
              background: applying ? '#6c757d' : '#28a745',
              color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600,
            }}>
              {applying ? t('updates.applying') : t('updates.apply_update')}
            </button>
            {applyError && <p style={{ color: '#dc3545', marginTop: 8 }}>{applyError}</p>}
            {state.applier.applied && (
              <p style={{ color: '#155724', marginTop: 8 }}>
                {t('updates.applied_version')}: {state.latest.version} ({state.applier.applied_at ? formatDate(state.applier.applied_at) : ''})
              </p>
            )}
          </section>
        )}

        {/* ── Settings ── */}
        <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <h2 style={{ marginTop: 0 }}>{t('updates.settings_title')}</h2>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <strong>{t('updates.check_interval')}</strong>
            <select
              value={state.settings.upd_check_h}
              onChange={e => setState(s => s ? { ...s, settings: { ...s.settings, upd_check_h: Number(e.target.value) } } : null)}
              style={{ display: 'block', marginTop: 4, padding: '4px 8px', borderRadius: 4, border: '1px solid var(--gray-300)' }}
            >
              {INTERVALS.map(i => (
                <option key={i.value} value={i.value}>{t(i.labelKey)}</option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <input
              type="checkbox"
              checked={state.settings.upd_apply_auto}
              onChange={e => setState(s => s ? { ...s, settings: { ...s.settings, upd_apply_auto: e.target.checked } } : null)}
            />
            {t('updates.apply_auto')}
          </label>
          <button onClick={handleSaveSettings} disabled={saving} style={{
            background: saving ? '#6c757d' : 'var(--blue)',
            color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600,
          }}>
            {saving ? t('updates.saving') : t('updates.save_settings')}
          </button>
          {saveError && <p style={{ color: '#dc3545', marginTop: 8 }}>{saveError}</p>}
          {state.request !== null && (
            <p style={{ color: '#004085', background: '#cce5ff', padding: '4px 12px', borderRadius: 4, marginTop: 12, fontWeight: 600 }}>
              {t('updates.pending_update')} {state.request.version} ({formatDate(state.request.requested_at)})
            </p>
          )}
        </section>

        {/* ── Applier status ── */}
        <section style={{ border: '1px solid var(--gray-300)', borderRadius: 8, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>{t('updates.applier_title')}</h2>
          {!state.applier.installed ? (
            <div style={{ color: '#856404', background: '#fff3cd', padding: 12, borderRadius: 4 }}>
              <p style={{ margin: '0 0 8px 0' }}>{t('updates.applier_not_installed')}</p>
              <p style={{ margin: 0 }}>{t('updates.applier_readme_section')}</p>
            </div>
          ) : (
            <>
              <p><strong>{t('updates.last_run')}</strong> {formatDate(state.applier.seen_at)}</p>
              <p><strong>{t('updates.last_version_applied')}</strong> {state.applier.applied ? state.latest.version : '—'}</p>
              <p><strong>{t('updates.last_result')}</strong> {state.applier.result || '—'}</p>
              {state.applier.running && (
                <p style={{ color: '#004085', background: '#cce5ff', padding: '4px 12px', borderRadius: 4, fontWeight: 600 }}>
                  {t('updates.applying_version')}: {state.latest.version} ({formatDate(state.applier.running_at)})
                </p>
              )}
            </>
          )}
        </section>
      </main>
    </>
  )
}
