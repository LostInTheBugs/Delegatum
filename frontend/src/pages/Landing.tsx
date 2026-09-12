import { Link } from 'react-router-dom'
import { useT, LANGS } from '../i18n/I18nContext'
import Footer from '../components/Footer'

export default function Landing() {
  const { t, lang, setLang } = useT()
  return (
    <div className="container" style={{ paddingTop: 10 }}>
      <div className="logo-area">
        <img src="/delegatum-lockup.png" className="logo-lockup" alt="Delegatum — Data Sovereignty" />
        <h1 className="sr-only">{t('landing.title')}</h1>
        <p className="subtitle">{t('landing.subtitle')}</p>
        {/* Sélecteur de langue compact — langue choisie ici appliquée au compte après login */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', alignItems: 'center' }}>
          <span aria-hidden="true">🌐</span>
          <select
            aria-label={t('landing.language', 'Langue')}
            value={lang}
            onChange={e => setLang(e.target.value as typeof lang)}
            style={{
              padding: '5px 10px', borderRadius: 999, border: '1px solid var(--gray-300)',
              background: '#fff', color: 'var(--gray-600)', fontSize: '.85rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            {LANGS.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </div>
      </div>
      <div className="card card-compact">
        <div className="btn-group">
          <Link to="/login" className="btn btn-primary">{t('landing.login')}</Link>
          <Link to="/join" className="btn btn-secondary">{t('landing.join')}</Link>
          <Link to="/create" className="btn btn-gold">{t('landing.create')}</Link>
        </div>
      </div>
      <p style={{ color: 'var(--gray-600)', fontSize: '.85rem', textAlign: 'center', marginTop: 8 }}>
        {t('landing.footer')}
      </p>
      <div style={{ background: '#fff3cd', border: '1px solid #ffc107', borderRadius: '8px', padding: '6px 12px', fontSize: '.68rem', color: '#856404', textAlign: 'center', maxWidth: '620px', margin: '8px auto 0' }}>
        ⚠️ <strong>Application expérimentale</strong> — Cet outil est fourni à titre de démonstration uniquement. Il ne constitue en aucun cas un conseil juridique et n'est pas garanti conforme à la législation luxembourgeoise. L'utilisation de cette application se fait aux risques et périls de l'utilisateur. Pour toute question relative au droit du travail luxembourgeois, consultez un professionnel qualifié ou la Chambre des Salariés (CSL).
      </div>
      <Footer />
    </div>
  )
}
