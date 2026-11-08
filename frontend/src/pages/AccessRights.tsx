import { useEffect, useState, useMemo } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useT } from '../i18n/I18nContext'
import NavBar from '../components/NavBar'
import * as api from '../api/client'

const LEVELS = ['none', 'read', 'write']
const EXTERIOR_ROLES = new Set(['salarie_designe', 'rh', 'itm', 'police'])

export default function AccessRights() {
  const { t } = useT()
  const { user, token } = useAuth()
  const [data, setData] = useState<api.PermissionMatrixResponse | null>(null)
  const [matrix, setMatrix] = useState<Record<string, Record<string, string>>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const is_admin = user?.role === 'admin'
  const levelLabel = (lvl: string) => t(`access.level.${lvl}`, lvl)

  // Initialize matrix from defaults on mount
  useEffect(() => {
    async function load() {
      try {
        const res = await api.getPermissions()
        setData(res)
        setMatrix(res.matrix)
      } catch (e: any) {
        setErr(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  const modules = useMemo(() => data?.modules ?? [], [data])
  const roles = useMemo(() => data?.roles ?? [], [data])

  function handleRole(role: string, module: string, value: string) {
    setMatrix(prev => ({
      ...prev,
      [role]: { ...prev[role], [module]: value },
    }))
  }

  async function handleSave() {
    setSaving(true); setErr(null); setMsg(null)
    try {
      const res = await api.updatePermissions(matrix)
      setData(res)
      setMatrix(res.matrix)
      setMsg(t('access.save_success'))
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    if (!data) return
    const defaults = data.defaults
    // Merge: admin stays write
    const merged: Record<string, Record<string, string>> = {}
    for (const role of roles) {
      merged[role] = {}
      for (const mod of modules) {
        if (role === 'admin') {
          merged[role][mod] = 'write'
        } else {
          merged[role][mod] = defaults[role]?.[mod] ?? 'none'
        }
      }
    }
    setMatrix(merged)
  }

  function cellValue(role: string, module: string): string {
    if (role === 'admin') return 'write'
    return matrix[role]?.[module] ?? 'none'
  }

  function cellOptions(role: string, module: string): string[] {
    if (role === 'admin') return ['write']
    if (EXTERIOR_ROLES.has(role) && module === 'meetings') return ['none']
    if (EXTERIOR_ROLES.has(role)) return ['none', 'read']
    return LEVELS
  }

  if (loading) return (
    <>
      <NavBar />
      <div className="dashboard"><div className="spinner" /></div>
    </>
  )

  if (!data) return (
    <>
      <NavBar />
      <div className="dashboard">
        {err && <div className="error-msg">{err}</div>}
        <p>{t('access.title')}</p>
      </div>
    </>
  )

  return (
    <>
      <NavBar />
      <div className="dashboard">
        {msg && <div className="success-msg">{msg}</div>}
        {err && <div className="error-msg">{err}</div>}

        <div className="card mb-24">
          <h2>{t('access.title')}</h2>
          <p style={{ color: 'var(--gray-600)', marginBottom: 16, fontSize: '.9rem' }}>
            {is_admin ? t('access.admin_hint') : t('access.readonly_hint')}
          </p>

          <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.82rem', minWidth: 600 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--gray-300)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 10px', position: 'sticky', left: 0, background: 'white', zIndex: 1, minWidth: 140 }}>
                    {t('access.role')}
                  </th>
                  {modules.map((mod: string) => (
                    <th key={mod} style={{ textAlign: 'center', padding: '8px 6px', whiteSpace: 'nowrap' }}>
                      {t(`access.module.${mod}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {roles.map((role: string) => {
                  const is_exterior = EXTERIOR_ROLES.has(role)
                  return (
                    <tr key={role} style={{ borderBottom: '1px solid var(--gray-200)' }}>
                      <td style={{ padding: '6px 10px', fontWeight: 500, position: 'sticky', left: 0, background: 'white', zIndex: 1 }}>
                        {t(`access.role.${role}`, role)}
                        {is_exterior && <span style={{ marginLeft: 4, fontSize: '.7rem', color: 'var(--gray-500)' }}>({t('access.external')})</span>}
                      </td>
                      {modules.map((mod: string) => {
                        const val = cellValue(role, mod)
                        const opts = cellOptions(role, mod)
                        const editable = is_admin && role !== 'admin'
                        const disabled = !editable || (role === 'admin') ||
                          (EXTERIOR_ROLES.has(role) && mod === 'meetings')
                        return (
                          <td key={mod} style={{ textAlign: 'center', padding: '4px 6px' }}>
                            <select
                              value={val}
                              onChange={e => handleRole(role, mod, e.target.value)}
                              disabled={disabled}
                              style={{
                                padding: '4px 8px',
                                border: '1.5px solid var(--gray-300)',
                                borderRadius: 'var(--radius)',
                                fontSize: '.8rem',
                                width: '100%',
                                background: disabled ? 'var(--gray-50)' : 'white',
                                cursor: disabled ? 'not-allowed' : 'pointer',
                                color: val === 'none' ? 'var(--gray-500)' : val === 'read' ? 'var(--blue)' : 'var(--green)',
                              }}
                            >
                              {opts.map(lvl => (
                                <option key={lvl} value={lvl}>{levelLabel(lvl)}</option>
                              ))}
                            </select>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {is_admin && (
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? t('access.saving') : t('access.save')}
              </button>
              <button className="btn" onClick={handleReset} disabled={saving}>
                {t('access.reset')}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
