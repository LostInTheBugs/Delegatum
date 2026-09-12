/**
 * Tests du helper de téléchargement — routage desktop (pywebview) vs navigateur.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { saveBlob, isDesktop } from './download'

function clearDesktop() {
  delete (window as any).pywebview
}

afterEach(() => {
  clearDesktop()
  vi.restoreAllMocks()
})

describe('saveBlob', () => {
  it('desktop : passe par l’API native save_file (base64, b64=true)', async () => {
    const save = vi.fn().mockResolvedValue({ ok: true, path: 'C:\\tmp\\x.pdf' })
    ;(window as any).pywebview = { api: { save_file: save } }
    expect(isDesktop()).toBe(true)

    await saveBlob('x.pdf', new Blob(['hello'], { type: 'application/pdf' }))

    expect(save).toHaveBeenCalledTimes(1)
    const [filename, content, path, b64] = save.mock.calls[0]
    expect(filename).toBe('x.pdf')
    expect(content).toBe(btoa('hello'))
    expect(path).toBeNull()
    expect(b64).toBe(true)
  })

  it('desktop : annulation silencieuse (cancelled)', async () => {
    const save = vi.fn().mockResolvedValue({ ok: false, cancelled: true })
    ;(window as any).pywebview = { api: { save_file: save } }
    await expect(saveBlob('x.pdf', new Blob(['x']))).resolves.toBeUndefined()
  })

  it('desktop : erreur remontée', async () => {
    const save = vi.fn().mockResolvedValue({ ok: false, error: 'disk-full' })
    ;(window as any).pywebview = { api: { save_file: save } }
    await expect(saveBlob('x.pdf', new Blob(['x']))).rejects.toThrow('disk-full')
  })

  it('navigateur : ancre + blob (sans pywebview)', async () => {
    clearDesktop()
    expect(isDesktop()).toBe(false)
    const createUrl = vi.fn().mockReturnValue('blob:fake')
    const revokeUrl = vi.fn()
    ;(URL as any).createObjectURL = createUrl
    ;(URL as any).revokeObjectURL = revokeUrl
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    await saveBlob('y.csv', new Blob(['a,b']))

    expect(createUrl).toHaveBeenCalledTimes(1)
    expect(click).toHaveBeenCalledTimes(1)
    expect(document.querySelector('a')).toBeNull() // ancre retirée du DOM
  })
})
