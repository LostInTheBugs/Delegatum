/**
 * PDF « dossier ITM » du registre sécurité/santé (Art. L.414-14).
 *
 * Pure function : prend les entrées + l'état d'intégrité et retourne les
 * octets du PDF. Mêmes conventions que pdfExport.ts / workforceStatsPdf.ts :
 * police Unicode embarquée, métadonnées purgées, aucune dépendance externe.
 *
 * Le PDF contient, en annexe, l'état d'intégrité (empreinte de chaîne SHA-256,
 * sceaux, empreinte du dossier JSON fourni à côté) + la procédure de
 * vérification indépendante.
 */

import { PDFDocument, rgb } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
import defaultFontUrl from '../assets/DejaVuSans.ttf?url'

const PAGE_WIDTH = 595.28 // A4 portrait (points)
const PAGE_HEIGHT = 841.89
const MARGIN = 50
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
const BOTTOM_LIMIT = 62

export interface RegisterPdfEntry {
  entry_date: string | null
  location: string
  description: string
  status: string
  chef_service_name: string
  countersigned_at: string | null
  voided_at: string | null
  void_reason: string
  delegate_name: string
  event_hash?: string | null
  voided_by_name?: string
}

export interface RegisterPdfSeal {
  sealed_at: string | null
  event_count: number
  head_signature: string
  tsa_status: string
}

export interface RegisterPdfIntegrity {
  eventCount: number
  headHash: string | null
  ok: boolean
  seals: RegisterPdfSeal[]
}

export interface RegisterPdfOptions {
  orgName: string
  entries: RegisterPdfEntry[]
  integrity: RegisterPdfIntegrity
  /** SHA-256 du dossier JSON d'intégrité fourni avec ce PDF (optionnel). */
  dossierDigest?: string | null
  fontBytes?: Uint8Array
  generatedAt?: Date
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = iso.slice(0, 10).split('-')
  if (d.length !== 3) return iso
  return `${d[2]}/${d[1]}/${d[0]}`
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return `${fmtDate(iso)} ${iso.slice(11, 16)}`.trim()
}

export async function exportSafetyRegisterPDF(opts: RegisterPdfOptions): Promise<Uint8Array> {
  let fontData: Uint8Array
  if (opts.fontBytes) {
    fontData = opts.fontBytes
  } else {
    const resp = await fetch(defaultFontUrl)
    if (!resp.ok) {
      throw new Error('Impossible de charger la police Unicode embarquée — export PDF impossible.')
    }
    fontData = new Uint8Array(await resp.arrayBuffer())
  }

  const pdf = await PDFDocument.create()
  pdf.registerFontkit(fontkit)
  const font = await pdf.embedFont(fontData)

  pdf.setTitle('')
  pdf.setAuthor('')
  pdf.setSubject('')
  pdf.setKeywords([])
  pdf.setProducer('')
  pdf.setCreator('')
  const neutralDate = new Date('2020-01-01T00:00:00Z')
  pdf.setCreationDate(neutralDate)
  pdf.setModificationDate(neutralDate)

  let page = pdf.addPage([PAGE_WIDTH, PAGE_HEIGHT])
  let y = PAGE_HEIGHT - MARGIN
  let pageNo = 1

  const wrap = (text: string, size: number, maxWidth: number): string[] => {
    const lines: string[] = []
    for (const para of text.split('\n')) {
      let cur = ''
      for (const word of para.split(/\s+/).filter(Boolean)) {
        const test = cur ? `${cur} ${word}` : word
        if (font.widthOfTextAtSize(test, size) <= maxWidth) {
          cur = test
        } else {
          if (cur) lines.push(cur)
          let w = word
          while (font.widthOfTextAtSize(w, size) > maxWidth) {
            let cut = w.length
            while (cut > 1 && font.widthOfTextAtSize(w.slice(0, cut), size) > maxWidth) cut -= 1
            lines.push(w.slice(0, cut))
            w = w.slice(cut)
          }
          cur = w
        }
      }
      if (cur) lines.push(cur)
    }
    return lines
  }

  const ensure = (needed: number): void => {
    if (y - needed < BOTTOM_LIMIT) {
      page.drawText('Registre spécial — art. L.414-14 du Code du travail luxembourgeois', {
        x: MARGIN, y: 38, size: 7.5, font, color: rgb(0.55, 0.55, 0.55),
      })
      page.drawText(`page ${pageNo}`, { x: PAGE_WIDTH - MARGIN - 40, y: 38, size: 7.5, font, color: rgb(0.55, 0.55, 0.55) })
      page = pdf.addPage([PAGE_WIDTH, PAGE_HEIGHT])
      pageNo += 1
      y = PAGE_HEIGHT - MARGIN
    }
  }

  const text = (
    str: string,
    o: { size?: number; color?: [number, number, number]; gap?: number; x?: number; maxWidth?: number } = {},
  ): void => {
    const size = o.size ?? 10
    const color = o.color ?? [0.1, 0.1, 0.1]
    const x = o.x ?? MARGIN
    const maxWidth = o.maxWidth ?? CONTENT_WIDTH - (x - MARGIN)
    for (const line of wrap(str, size, maxWidth)) {
      ensure(size + 4)
      page.drawText(line, { x, y, size, font, color: rgb(color[0], color[1], color[2]) })
      y -= size + (o.gap ?? 3)
    }
  }

  // ── En-tête ──
  text('Registre spécial de sécurité et de santé', { size: 17, gap: 5 })
  text(opts.orgName, { size: 11, color: [0.25, 0.25, 0.25], gap: 4 })
  const genAt = opts.generatedAt ?? new Date()
  const genStr = `${String(genAt.getDate()).padStart(2, '0')}/${String(genAt.getMonth() + 1).padStart(2, '0')}/${genAt.getFullYear()}`
  text(
    `Art. L.414-14 du Code du travail — constatations du délégué à la sécurité et à la santé, ` +
      `contresignées par le chef de service. Document généré le ${genStr} — ${opts.entries.length} constatation(s).`,
    { size: 8.5, color: [0.45, 0.45, 0.45], gap: 2 },
  )
  y -= 6
  page.drawLine({
    start: { x: MARGIN, y }, end: { x: PAGE_WIDTH - MARGIN, y },
    thickness: 0.8, color: rgb(0.75, 0.75, 0.78),
  })
  y -= 16

  // ── Entrées (ordre chronologique) ──
  const sorted = [...opts.entries].sort((a, b) =>
    (a.entry_date ?? '').localeCompare(b.entry_date ?? ''),
  )
  if (sorted.length === 0) {
    text('Aucune constatation au registre.', { size: 10, color: [0.4, 0.4, 0.4] })
  }
  for (const e of sorted) {
    ensure(60)
    const head = [fmtDate(e.entry_date), e.location || null].filter(Boolean).join(' · ')
    text(head, { size: 10.5, gap: 2 })
    text(e.description, { size: 10, gap: 2 })
    const by = e.delegate_name ? `par ${e.delegate_name}` : ''
    if (e.status === 'voided') {
      const parts = [
        `ANNULÉE le ${fmtDateTime(e.voided_at)}`,
        e.voided_by_name ? `par ${e.voided_by_name}` : '',
        e.void_reason ? `— Motif : ${e.void_reason}` : '',
      ].filter(Boolean)
      text(parts.join(' '), { size: 8.5, color: [0.65, 0.12, 0.12], gap: 2 })
    } else if (e.status === 'countersigned' && e.chef_service_name) {
      text(
        `Contresigné par ${e.chef_service_name} le ${fmtDateTime(e.countersigned_at)}${by ? ` · constatation du délégué ${by}` : ''}`,
        { size: 8.5, color: [0.15, 0.45, 0.2], gap: 2 },
      )
    } else {
      text(`En attente de contreseing${by ? ` (constatation ${by})` : ''}`, { size: 8.5, color: [0.65, 0.4, 0.05], gap: 2 })
    }
    if (e.event_hash) {
      text(`Empreinte du journal : ${e.event_hash.slice(0, 24)}…`, { size: 7.5, color: [0.5, 0.5, 0.5], gap: 2 })
    }
    y -= 6
    page.drawLine({
      start: { x: MARGIN, y }, end: { x: PAGE_WIDTH - MARGIN, y },
      thickness: 0.4, color: rgb(0.85, 0.85, 0.85),
    })
    y -= 12
  }

  // ── Annexe d'intégrité ──
  y -= 8
  text('Annexe — intégrité du registre (chaîne SHA-256)', { size: 12.5, gap: 4 })
  text(`Événements chaînés : ${opts.integrity.eventCount}`, { size: 9.5, gap: 2 })
  text(`Empreinte finale de la chaîne : ${opts.integrity.headHash ?? '—'}`, { size: 9.5, gap: 2 })
  text(`Vérification au moment de la génération : ${opts.integrity.ok ? 'CONFORME' : 'ANOMALIE DÉTECTÉE'}`, {
    size: 9.5,
    color: opts.integrity.ok ? [0.15, 0.45, 0.2] : [0.7, 0.1, 0.1],
    gap: 2,
  })
  if (opts.dossierDigest) {
    text(`Empreinte SHA-256 du dossier d'intégrité (fichier JSON joint) : ${opts.dossierDigest}`, { size: 8.5, color: [0.35, 0.35, 0.35], gap: 2 })
  }
  if (opts.integrity.seals.length === 0) {
    text('Sceaux : aucun pour le moment.', { size: 9, color: [0.4, 0.4, 0.4], gap: 2 })
  } else {
    text('Sceaux (empreinte figée + horodatage RFC 3161) :', { size: 9, gap: 2 })
    for (const s of [...opts.integrity.seals].sort((a, b) => (a.sealed_at ?? '').localeCompare(b.sealed_at ?? ''))) {
      text(
        `· ${fmtDateTime(s.sealed_at)} — ${s.event_count} événement(s) — empreinte ${s.head_signature}… — horodatage : ${s.tsa_status}`,
        { size: 8.5, color: [0.35, 0.35, 0.35], gap: 2 },
      )
    }
  }
  y -= 4
  text(
    "Procédure de vérification indépendante : chaque événement du journal est haché selon " +
      "sha256(prev_hash + '|' + payload_json). Le dossier d'intégrité (JSON) fourni avec ce document " +
      "contient le journal complet, les sceaux et les jetons d'horodatage RFC 3161 ; il se vérifie en ligne " +
      "(page /verify de l'application) ou manuellement. Jeton RFC 3161 : « openssl ts -reply -in token.tsr -text » ; " +
      "empreinte du manifeste horodaté : « openssl dgst -sha256 manifest.txt ».",
    { size: 8.5, color: [0.45, 0.45, 0.45], gap: 2 },
  )

  ensure(30)
  page.drawText('Registre spécial — art. L.414-14 du Code du travail luxembourgeois', {
    x: MARGIN, y: 38, size: 7.5, font, color: rgb(0.55, 0.55, 0.55),
  })
  page.drawText(`page ${pageNo}`, { x: PAGE_WIDTH - MARGIN - 40, y: 38, size: 7.5, font, color: rgb(0.55, 0.55, 0.55) })

  return pdf.save()
}
