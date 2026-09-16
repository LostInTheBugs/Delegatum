import { describe, expect, it, beforeAll } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { PDFDocument } from 'pdf-lib'
import { PDFParse } from 'pdf-parse'
import { exportSafetyRegisterPDF, type RegisterPdfEntry } from './registerPdf'

let fontBytes: Uint8Array

beforeAll(() => {
  const fontPath = resolve(__dirname, '..', 'assets', 'DejaVuSans.ttf')
  fontBytes = new Uint8Array(readFileSync(fontPath))
})

const ENTRIES: RegisterPdfEntry[] = [
  {
    entry_date: '2026-09-01', location: 'Atelier 2', description: "Fuite d'eau au plafond près de la machine 4",
    status: 'countersigned', chef_service_name: 'M. Kirch', countersigned_at: '2026-09-02T09:30:00',
    voided_at: null, void_reason: '', delegate_name: 'Sophie Muller', event_hash: 'a'.repeat(64),
  },
  {
    entry_date: '2026-09-05', location: 'Réfectoire', description: 'Fenêtre qui ferme mal',
    status: 'pending', chef_service_name: '', countersigned_at: null,
    voided_at: null, void_reason: '', delegate_name: 'Marc Weber', event_hash: 'b'.repeat(64),
  },
  {
    entry_date: '2026-09-07', location: 'Sous-sol', description: 'Extincteur manquant',
    status: 'voided', chef_service_name: '', countersigned_at: null,
    voided_at: '2026-09-08T10:00:00', void_reason: 'Doublon de la constatation du 28/08',
    delegate_name: 'Marc Weber', voided_by_name: 'Sophie Muller', event_hash: 'c'.repeat(64),
  },
]

async function extractText(bytes: Uint8Array): Promise<string> {
  const parser = new PDFParse({ data: bytes as unknown as Buffer })
  const result = await parser.getText()
  return result.text
}

let bytes: Uint8Array
let doc: PDFDocument

beforeAll(async () => {
  bytes = await exportSafetyRegisterPDF({
    orgName: 'Demo SARL',
    entries: ENTRIES,
    integrity: {
      eventCount: 42,
      headHash: 'f'.repeat(64),
      ok: true,
      seals: [{ sealed_at: '2026-09-15T05:00:00', event_count: 42, head_signature: 'abc123def4567890', tsa_status: 'ok' }],
    },
    dossierDigest: 'd'.repeat(64),
    fontBytes,
    generatedAt: new Date('2026-09-16T12:00:00Z'),
  })
  doc = await PDFDocument.load(bytes)
})

describe('exportSafetyRegisterPDF', () => {
  it('produces a valid PDF', () => {
    expect(bytes[0]).toBe(0x25)
    expect(bytes[1]).toBe(0x50)
    expect(bytes[2]).toBe(0x44)
    expect(bytes[3]).toBe(0x46)
    expect(doc.getPageCount()).toBeGreaterThanOrEqual(1)
    const { width, height } = doc.getPages()[0].getSize()
    expect(width).toBeCloseTo(595.28, 0)
    expect(height).toBeCloseTo(841.89, 0)
  })

  it('contains entries, legal reference and integrity annex', async () => {
    const text = await extractText(bytes)
    expect(text).toContain('L.414-14')
    expect(text).toContain('Demo SARL')
    expect(text).toContain("Fuite d'eau au plafond")
    expect(text).toContain('Contresigné par M. Kirch')
    expect(text).toContain('En attente de contreseing')
    expect(text).toContain('ANNULÉE')
    expect(text).toContain('Motif : Doublon')
    expect(text).toContain('Annexe')
    expect(text).toContain('42')                    // événements chaînés
    expect(text).toContain('ffffffff')              // empreinte finale
    expect(text).toContain('dddddddd')              // empreinte du dossier JSON
    expect(text).toContain('abc123def4567890')      // signature du sceau
  })

  it('purges metadata', () => {
    const rawPdf = Buffer.from(bytes).toString('latin1')
    expect(rawPdf).not.toContain('pdf-lib')
    expect(rawPdf).not.toContain('Hopding')
    expect(doc.getTitle() || '').toBe('')
    expect(doc.getCreator() || '').toBe('')
  })

  it('handles an empty register', async () => {
    const empty = await exportSafetyRegisterPDF({
      orgName: 'Demo SARL',
      entries: [],
      integrity: { eventCount: 0, headHash: null, ok: true, seals: [] },
      fontBytes,
    })
    const d = await PDFDocument.load(empty)
    expect(d.getPageCount()).toBe(1)
    const text = await extractText(empty)
    expect(text).toContain('Aucune constatation')
    expect(text).toContain('aucun pour le moment')
  })
})
