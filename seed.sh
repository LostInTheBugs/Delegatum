#!/bin/bash
# Script de seed — crée les comptes de test après un déploiement
HOST=${1:-localhost:3002}

echo "🌱 Seeding $HOST ..."

# Helper: fetch a CAPTCHA challenge, compute the answer, output "challenge_id:answer"
fetch_captcha() {
  local resp=$(curl -sf "$HOST/api/auth/captcha")
  local cid=$(echo "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["challenge_id"])')
  local question=$(echo "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["question"])')
  # question format: "Combien font A + B ?"
  local a=$(echo "$question" | sed 's/.*font \([0-9]*\) + \([0-9]*\).*/\1/')
  local b=$(echo "$question" | sed 's/.*font \([0-9]*\) + \([0-9]*\).*/\2/')
  local ans=$((a + b))
  echo "${cid}:${ans}"
}

# 1. Créer l'organisation + admin (Présidente)
CAPTCHA=$(fetch_captcha)
CID="${CAPTCHA%%:*}"
CANS="${CAPTCHA##*:}"
curl -sf -X POST "$HOST/api/organizations" -H 'Content-Type: application/json' \
  -d "{\"organization_name\":\"Demo\",\"employee_count\":120,\"admin_email\":\"sophie@demo.lu\",\"admin_password\":\"demo123456\",\"admin_first_name\":\"Sophie\",\"admin_last_name\":\"Muller\",\"admin_delegue_status\":\"titulaire\",\"admin_delegue_role\":\"president\",\"captcha_id\":\"$CID\",\"captcha_answer\":\"$CANS\"}" >/dev/null && echo "  admin (Sophie Muller - Présidente) OK"

# Login pour récupérer le token admin
CAPTCHA=$(fetch_captcha)
CID="${CAPTCHA%%:*}"
CANS="${CAPTCHA##*:}"
TOK=$(curl -sf -X POST "$HOST/api/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"sophie@demo.lu\",\"password\":\"demo123456\",\"captcha_id\":\"$CID\",\"captcha_answer\":\"$CANS\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# Fonction pour créer un compte
invite_and_join() {
  local email=$1 first=$2 last=$3 status=$4 role=$5
  local CODE=$(curl -sf -X POST "$HOST/api/invitations" -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"first_name\":\"$first\",\"last_name\":\"$last\",\"delegue_status\":\"$status\",\"delegue_role\":\"$role\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["code"])')
  CAPTCHA=$(fetch_captcha)
  CID="${CAPTCHA%%:*}"
  CANS="${CAPTCHA##*:}"
  curl -sf -X POST "$HOST/api/join" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"demo123456\",\"first_name\":\"$first\",\"last_name\":\"$last\",\"invitation_code\":\"$CODE\",\"captcha_id\":\"$CID\",\"captcha_answer\":\"$CANS\"}" >/dev/null
  echo "  $first $last ($role) OK"
}

# Bureau
invite_and_join "marc@demo.lu" "Marc" "Weber" "titulaire" "vice_president"
invite_and_join "laura@demo.lu" "Laura" "Schmit" "titulaire" "secretaire"

# Titulaires restants
invite_and_join "tom@demo.lu" "Tom" "Wagner" "titulaire" "membre"
invite_and_join "emma@demo.lu" "Emma" "Kirsch" "titulaire" "membre"

# Suppléants
invite_and_join "paul@demo.lu" "Paul" "Hoffmann" "suppleant" "membre"
invite_and_join "anna@demo.lu" "Anna" "Klein" "suppleant" "membre"
invite_and_join "david@demo.lu" "David" "Fischer" "suppleant" "membre"
invite_and_join "clara@demo.lu" "Clara" "Becker" "suppleant" "membre"
invite_and_join "lucas@demo.lu" "Lucas" "Thill" "suppleant" "membre"

# 4. Délégué sécurité/santé + registre S&S (constats d'exemple — art. L.414-14)
login_token() {
  local email=$1
  CAPTCHA=$(fetch_captcha)
  CID="${CAPTCHA%%:*}"
  CANS="${CAPTCHA##*:}"
  curl -sf -X POST "$HOST/api/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"demo123456\",\"captcha_id\":\"$CID\",\"captcha_answer\":\"$CANS\"}" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
}

MARC_TOK=$(login_token "marc@demo.lu")
MARC_ID=$(curl -sf "$HOST/api/organization/members" -H "Authorization: Bearer $MARC_TOK" \
  | python3 -c 'import sys,json; print([m["id"] for m in json.load(sys.stdin) if m["email"]=="marc@demo.lu"][0])')
curl -sf -X PUT "$HOST/api/organization/members/$MARC_ID/designate" \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"field":"securite_sante","value":true}' >/dev/null && echo "  Marc Weber désigné délégué sécurité/santé"

# Constats d'exemple — uniquement si le registre est vide (re-seed sans doublons)
NB=$(curl -sf "$HOST/api/safety-register" -H "Authorization: Bearer $MARC_TOK" \
  | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
if [ "$NB" = "0" ]; then
  D1=$(date -d "-12 days" +%F); D2=$(date -d "-8 days" +%F); D3=$(date -d "-3 days" +%F)
  add_entry() {
    curl -sf -X POST "$HOST/api/safety-register" -H "Authorization: Bearer $MARC_TOK" -H 'Content-Type: application/json' \
      -d "{\"entry_date\":\"$1\",\"location\":\"$2\",\"description\":\"$3\"}" \
      | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])'
  }
  E1=$(add_entry "$D1" "Atelier 2" "Éclairage défectueux au-dessus de la machine 4 — risque en zone de passage")
  E2=$(add_entry "$D2" "Sous-sol" "Extincteur du local technique : contrôle annuel dépassé")
  E3=$(add_entry "$D3" "Réfectoire" "Fenêtre qui ferme mal — courant d’air, chauffage qui tourne à vide")
  curl -sf -X POST "$HOST/api/safety-register/$E1/countersign" -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
    -d '{"chef_service_name":"M. Reuter (chef d’atelier)"}' >/dev/null
  curl -sf -X POST "$HOST/api/safety-register/$E2/countersign" -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
    -d '{"chef_service_name":"Mme Wagner (responsable bâtiment)"}' >/dev/null
  echo "  registre S&S : 3 constats d'exemple (2 contresignés, 1 en attente)"
fi

echo "✅ Seed terminé"
