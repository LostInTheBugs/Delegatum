/**
 * Vérification d'un dossier d'intégrité du registre sécurité/santé (art. L.414-14).
 *
 * Le dossier (« registre_securite_integrite_*.json ») est autoportant : il
 * contient le registre, le journal chaîné complet et les sceaux. La
 * vérification s'exécute intégralement dans le navigateur (WebCrypto) — rien
 * n'est envoyé au serveur.
 *
 * Règle de hachage (identique au serveur, cf. backend/services/register_chain.py) :
 *   event_hash = sha256(prev_hash + "|" + payload_json)   [UTF-8 → hex minuscule]
 */

const GENESIS = '0'.repeat(64)

export interface DossierEvent {
  id: number
  entry_id: number | null
  action: string
  actor_name: string
  at: string | null
  payload_json: string
  prev_hash: string
  event_hash: string
}

export interface DossierEntry {
  id: number
  entry_date: string | null
  location: string
  description: string
  status: string
  chef_service_name: string
  countersigned_at: string | null
  voided_at: string | null
  void_reason: string
  delegate_name?: string
  created_by_name?: string
  event_hash?: string | null
}

export interface DossierSeal {
  id: number
  sealed_at: string | null
  event_count: number
  head_hash: string
  manifest: string
  tsa_status: string
  tsa_url: string | null
  tsa_token_b64?: string | null
  auto?: boolean
}

export interface Dossier {
  format?: string
  version?: number
  generated_at?: string
  organization?: { id?: number; name?: string }
  chain?: { genesis?: string; event_count?: number; head_hash?: string | null; hash_rule?: string }
  entries?: DossierEntry[]
  events?: DossierEvent[]
  seals?: DossierSeal[]
  verification?: unknown
}

export interface FieldMismatch {
  entry_id: number
  field: string
  expected: string
  actual: string
}

export interface VerifyResult {
  ok: boolean
  eventCount: number
  headHash: string | null
  chainOk: boolean
  firstBrokenIndex: number | null
  projectionOk: boolean
  mismatches: FieldMismatch[]
  sealsOk: boolean
  sealsChecked: number
  brokenSeals: number[]
  orgName: string | null
  generatedAt: string | null
}

/** SHA-256 hex (minuscules) — WebCrypto si disponible, repli pur JS sinon.

 * Le repli permet à la page /verify de fonctionner aussi en contexte non
 * sécurisé (déploiement HTTP sur réseau local) — l'API WebCrypto n'y est
 * pas exposée. Les deux implémentations sont testées sur les mêmes vecteurs.
 */
export async function sha256Hex(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle
  if (subtle) {
    const digest = await subtle.digest('SHA-256', new TextEncoder().encode(text))
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
  }
  return sha256HexPure(text)
}

const _K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

const rotr = (x: number, n: number): number => ((x >>> n) | (x << (32 - n))) >>> 0

/** SHA-256 pur JS (contexte non sécurisé) — mêmes vecteurs que WebCrypto. */
export function sha256HexPure(text: string): string {
  const bytes = new TextEncoder().encode(text)
  const l = bytes.length
  const bitLenHi = Math.floor(l / 536870912)
  const bitLenLo = (l << 3) >>> 0
  const padded = new Uint8Array((((l + 8) >> 6) + 1) << 6)
  padded.set(bytes)
  padded[l] = 0x80
  const dv = new DataView(padded.buffer)
  dv.setUint32(padded.length - 8, bitLenHi)
  dv.setUint32(padded.length - 4, bitLenLo)

  let [h0, h1, h2, h3, h4, h5, h6, h7] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]
  const w = new Uint32Array(64)
  for (let i = 0; i < padded.length; i += 64) {
    for (let j = 0; j < 16; j++) w[j] = dv.getUint32(i + j * 4)
    for (let j = 16; j < 64; j++) {
      const x = w[j - 15]
      const y = w[j - 2]
      const s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)
      const s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10)
      w[j] = (w[j - 16] + s0 + w[j - 7] + s1) >>> 0
    }
    let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7
    for (let j = 0; j < 64; j++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const t1 = (h + S1 + ch + _K[j] + w[j]) >>> 0
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const t2 = (S0 + maj) >>> 0
      h = g
      g = f
      f = e
      e = (d + t1) >>> 0
      d = c
      c = b
      b = a
      a = (t1 + t2) >>> 0
    }
    h0 = (h0 + a) >>> 0
    h1 = (h1 + b) >>> 0
    h2 = (h2 + c) >>> 0
    h3 = (h3 + d) >>> 0
    h4 = (h4 + e) >>> 0
    h5 = (h5 + f) >>> 0
    h6 = (h6 + g) >>> 0
    h7 = (h7 + h) >>> 0
  }
  return [h0, h1, h2, h3, h4, h5, h6, h7].map((x) => x.toString(16).padStart(8, '0')).join('')
}

export function parseDossier(text: string): Dossier {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('bad_file')
  }
  const d = data as Dossier
  if (!d || typeof d !== 'object' || d.format !== 'delegatum-safety-register-integrity') {
    throw new Error('bad_file')
  }
  return d
}

const norm = (v: unknown): string => (v === null || v === undefined ? 'null' : String(v))

/** Rejoue le journal → état attendu par entrée (miroir de replay_entries côté serveur). */
export function replayEntries(events: DossierEvent[]): Map<number, Record<string, unknown>> {
  const states = new Map<number, Record<string, unknown>>()
  for (const ev of events) {
    let p: Record<string, unknown>
    try {
      p = JSON.parse(ev.payload_json)
    } catch {
      continue
    }
    const eid = p.entry_id as number | null | undefined
    if (eid === null || eid === undefined) continue
    let st = states.get(eid)
    if (!st) {
      st = {}
      states.set(eid, st)
    }
    if (p.action === 'create') {
      st.entry_date = p.entry_date ?? null
      st.location = p.location ?? ''
      st.description = p.description ?? ''
      st.status = 'pending'
      st.chef_service_name = ''
      st.countersigned_at = null
      st.void_reason = ''
      st.voided_at = null
    } else if (p.action === 'countersign') {
      st.status = 'countersigned'
      st.chef_service_name = p.chef_service_name ?? ''
      st.countersigned_at = p.countersigned_at ?? null
    } else if (p.action === 'void') {
      st.status = 'voided'
      st.void_reason = p.reason ?? ''
      st.voided_at = p.voided_at ?? null
    }
  }
  return states
}

const VERIFIED_FIELDS = [
  'entry_date', 'location', 'description', 'status',
  'chef_service_name', 'countersigned_at', 'void_reason', 'voided_at',
] as const

export async function verifyDossier(dossier: Dossier): Promise<VerifyResult> {
  const genesis = dossier.chain?.genesis || GENESIS
  const events = [...(dossier.events ?? [])].sort((a, b) => a.id - b.id)

  // 1. Chaîne : chaque maillon doit se recalculer
  let prev = genesis
  let chainOk = true
  let firstBrokenIndex: number | null = null
  for (let i = 0; i < events.length; i++) {
    const ev = events[i]
    const h = await sha256Hex(prev + '|' + ev.payload_json)
    if (ev.prev_hash !== prev || ev.event_hash !== h) {
      chainOk = false
      firstBrokenIndex = i
      break
    }
    prev = ev.event_hash
  }

  // 2. Projection : le registre affiché doit correspondre au journal rejoué
  const states = replayEntries(events)
  const mismatches: FieldMismatch[] = []
  for (const e of dossier.entries ?? []) {
    const st = states.get(e.id)
    if (!st) {
      mismatches.push({ entry_id: e.id, field: '*', expected: '(aucun événement)', actual: '(entrée présente)' })
      continue
    }
    const actual: Record<string, unknown> = {
      entry_date: e.entry_date ?? null,
      location: e.location ?? '',
      description: e.description ?? '',
      status: e.status,
      chef_service_name: e.chef_service_name ?? '',
      countersigned_at: e.countersigned_at ?? null,
      void_reason: e.void_reason ?? '',
      voided_at: e.voided_at ?? null,
    }
    for (const f of VERIFIED_FIELDS) {
      if (norm(st[f]) !== norm(actual[f])) {
        mismatches.push({
          entry_id: e.id,
          field: f,
          expected: norm(st[f]).slice(0, 120),
          actual: norm(actual[f]).slice(0, 120),
        })
      }
    }
  }

  // 3. Sceaux : l'empreinte scellée doit correspondre au maillon n° {event_count}
  let sealsOk = true
  const brokenSeals: number[] = []
  for (const s of dossier.seals ?? []) {
    let expectedHead: string | null
    if (s.event_count === 0) expectedHead = genesis
    else if (s.event_count <= events.length) expectedHead = events[s.event_count - 1].event_hash
    else expectedHead = null
    const manifestOk = typeof s.manifest === 'string' && s.manifest.includes(`head_hash: ${s.head_hash}`)
    if (expectedHead !== s.head_hash || !manifestOk) {
      sealsOk = false
      brokenSeals.push(s.id)
    }
  }

  return {
    ok: chainOk && mismatches.length === 0 && sealsOk,
    eventCount: events.length,
    headHash: dossier.chain?.head_hash ?? (events.length ? events[events.length - 1].event_hash : null),
    chainOk,
    firstBrokenIndex,
    projectionOk: mismatches.length === 0,
    mismatches,
    sealsOk,
    sealsChecked: (dossier.seals ?? []).length,
    brokenSeals,
    orgName: dossier.organization?.name ?? null,
    generatedAt: dossier.generated_at ?? null,
  }
}
