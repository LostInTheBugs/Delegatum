"""Middleware : refuse les accès directs au backend.

Le backend n'est exposé que sur le réseau privé `sd-net` (derrière nginx).
Si `X-Real-Client-IP` est absent, la requête vient d'un accès direct
(bypass nginx) → refus 403.

Nginx ne définit ce header QUE lorsqu'il est présent en entrée
(cf-Connecting-IP via Cloudflare), ce qui garantit qu'aucun client
extern ne peut le spoof.
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse


async def reject_direct_access(request: Request, call_next):
    """Bloque les accès directs au backend (bypass nginx).

    En mode test (SD_TEST_MODE=1), le middleware est désactivé
    pour que FastAPI TestClient fonctionne correctement.
    """
    if os.getenv("SD_TEST_MODE") == "1":
        return await call_next(request)

    # Si X-Real-Client-IP est absent, c'est un accès direct
    if not request.headers.get("x-real-client-ip"):
        return JSONResponse(
            status_code=403,
            content={"detail": "Accès direct au backend refusé — passez par nginx"},
        )
    response = await call_next(request)
    return response
