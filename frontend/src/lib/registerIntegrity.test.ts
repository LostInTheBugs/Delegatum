import { describe, expect, it } from 'vitest'
import { createHash } from 'crypto'
import { parseDossier, sha256Hex, sha256HexPure, verifyDossier, type Dossier } from './registerIntegrity'

const GENESIS = '0'.repeat(64)

function eventHash(prev: string, payloadJson: string): string {
  return createHash('sha256').update(`${prev}|${payloadJson}`, 'utf8').digest('hex')
}

/** Dossier conforme au format serveur (backend/services/register_chain.py). */
function buildDossier(): Dossier {
  const payloads = [
    JSON.stringify({
      action: 'create', at: '2026-09-01T08:00:00', entry_date: '2026-09-01', entry_id: 1,
      description: "Fuite d'eau au plafond", location: 'Atelier 2', delegate_id: 2,
    }),
    JSON.stringify({
      action: 'countersign', at: '2026-09-02T09:00:00', countersigned_at: '2026-09-02T09:00:00',
      chef_service_name: 'M. Kirch', entry_id: 1,
    }),
  ]
  const events = []
  let prev = GENESIS
  for (let i = 0; i < payloads.length; i++) {
    const h = eventHash(prev, payloads[i])
    events.push({
      id: i + 1,
      entry_id: 1,
      action: i === 0 ? 'create' : 'countersign',
      actor_name: 'Sophie Muller',
      at: i === 0 ? '2026-09-01T08:00:00' : '2026-09-02T09:00:00',
      payload_json: payloads[i],
      prev_hash: prev,
      event_hash: h,
    })
    prev = h
  }
  const head = prev
  return {
    format: 'delegatum-safety-register-integrity',
    version: 1,
    generated_at: '2026-09-16T10:00:00',
    organization: { id: 1, name: 'Demo' },
    chain: { genesis: GENESIS, event_count: events.length, head_hash: head, hash_rule: "sha256_hex(prev_hash + '|' + payload_json_utf8)" },
    entries: [
      {
        id: 1, entry_date: '2026-09-01', location: 'Atelier 2', description: "Fuite d'eau au plafond",
        status: 'countersigned', chef_service_name: 'M. Kirch', countersigned_at: '2026-09-02T09:00:00',
        voided_at: null, void_reason: '',
      },
    ],
    events,
    seals: [
      {
        id: 1, sealed_at: '2026-09-03T05:00:00', event_count: 2, head_hash: head,
        manifest: `DELEGATUM SAFETY REGISTER v1\norg_id: 1\nhead_hash: ${head}\n`, tsa_status: 'ok', tsa_url: 'http://tsa.test',
      },
    ],
  }
}

describe('sha256Hex', () => {
  it('correspond au vecteur de test SHA-256', async () => {
    expect(await sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  })
})

describe('sha256HexPure (repli contexte non sécurisé)', () => {
  const VECTORS: [string, string][] = [
    ['', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'],
    ['abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'],
    ['abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
      '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'],
  ]

  it('reproduit les vecteurs standards et les chaînes UTF-8', () => {
    for (const [input, expected] of VECTORS) {
      expect(sha256HexPure(input)).toBe(expected)
    }
    const utf8 = "Fuite d'eau au plafond — Atelier 2 🇱🇺"
    expect(sha256HexPure(utf8)).toBe(createHash('sha256').update(utf8, 'utf8').digest('hex'))
  })

  it('gère les messages multi-blocs (longueur > 64 octets)', () => {
    const long = 'x'.repeat(1000)
    expect(sha256HexPure(long)).toBe(createHash('sha256').update(long, 'utf8').digest('hex'))
  })

  it('sha256Hex retombe sur le repli quand WebCrypto est absent', async () => {
    expect(sha256HexPure('abc')).toBe(await sha256Hex('abc'))
  })
})

describe('parseDossier', () => {
  it('rejette un JSON étranger', () => {
    expect(() => parseDossier('{"x":1}')).toThrow()
    expect(() => parseDossier('not json')).toThrow()
  })
  it('accepte un dossier au bon format', () => {
    expect(parseDossier(JSON.stringify(buildDossier())).format).toBe('delegatum-safety-register-integrity')
  })
})

describe('verifyDossier', () => {
  it('valide un dossier intact (chaîne + projection + sceaux)', async () => {
    const r = await verifyDossier(buildDossier())
    expect(r.ok).toBe(true)
    expect(r.chainOk).toBe(true)
    expect(r.projectionOk).toBe(true)
    expect(r.sealsOk).toBe(true)
    expect(r.eventCount).toBe(2)
    expect(r.sealsChecked).toBe(1)
    expect(r.headHash).toHaveLength(64)
  })

  it('détecte un payload réécrit (chaîne cassée)', async () => {
    const d = buildDossier()
    d.events![0].payload_json = d.events![0].payload_json.replace('Fuite', 'Inondation')
    const r = await verifyDossier(d)
    expect(r.chainOk).toBe(false)
    expect(r.firstBrokenIndex).toBe(0)
    expect(r.ok).toBe(false)
  })

  it('détecte la suppression d’un maillon', async () => {
    const d = buildDossier()
    d.events = [d.events![1]]
    const r = await verifyDossier(d)
    expect(r.chainOk).toBe(false)
    expect(r.ok).toBe(false)
  })

  it('détecte une entrée réécrite hors journal (projection)', async () => {
    const d = buildDossier()
    d.entries![0].description = 'Description modifiée'
    const r = await verifyDossier(d)
    expect(r.chainOk).toBe(true)
    expect(r.projectionOk).toBe(false)
    expect(r.mismatches.some((m) => m.field === 'description')).toBe(true)
    expect(r.ok).toBe(false)
  })

  it('détecte une entrée absente du journal', async () => {
    const d = buildDossier()
    d.entries!.push({ id: 99, entry_date: '2026-01-01', location: '', description: 'Fantôme', status: 'pending', chef_service_name: '', countersigned_at: null, voided_at: null, void_reason: '' })
    const r = await verifyDossier(d)
    expect(r.projectionOk).toBe(false)
    expect(r.mismatches.some((m) => m.entry_id === 99 && m.field === '*')).toBe(true)
  })

  it('détecte un sceau qui ne correspond plus à la chaîne', async () => {
    const d = buildDossier()
    d.seals![0].event_count = 1 // le sceau prétend sceller 1 événement, l'empreinte est celle du 2e
    const r = await verifyDossier(d)
    expect(r.sealsOk).toBe(false)
    expect(r.brokenSeals).toEqual([1])
    expect(r.ok).toBe(false)
  })

  it('valide un dossier sans sceau ni événement', async () => {
    const d = buildDossier()
    d.events = []
    d.entries = []
    d.seals = []
    d.chain!.head_hash = null
    d.chain!.event_count = 0
    const r = await verifyDossier(d)
    expect(r.ok).toBe(true)
    expect(r.eventCount).toBe(0)
  })
})
