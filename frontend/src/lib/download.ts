/**
 * Téléchargements de fichiers — compatible app de bureau (Delegatum Desktop).
 *
 * Dans la WebView Windows (pywebview/WebView2) les téléchargements
 * `<a download>` sont bloqués silencieusement (vécu sur Patrimony Desktop) :
 * on passe alors par l'API native `DesktopApi.save_file` du launcher
 * (dialogue « Enregistrer sous », contenu transmis en base64 pour les
 * fichiers binaires PDF/CSV/ZIP/EML).
 *
 * Navigateur classique : blob + ancre comme avant.
 */

export function isDesktop(): boolean {
  const w = window as unknown as { pywebview?: { api?: { save_file?: unknown } } }
  return !!(w.pywebview && w.pywebview.api && w.pywebview.api.save_file)
}

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let bin = ''
  const CHUNK = 0x8000
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK))
  }
  return btoa(bin)
}

/** Enregistre un blob sous `filename` (natif en desktop, téléchargement sinon). */
export async function saveBlob(filename: string, blob: Blob): Promise<void> {
  if (isDesktop()) {
    const api = (window as any).pywebview.api
    const b64 = toBase64(await blob.arrayBuffer())
    const res = await api.save_file(filename, b64, null, true)
    if (res && res.cancelled) return
    if (res && res.ok === false) throw new Error(res.error || 'Enregistrement impossible')
    return
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
