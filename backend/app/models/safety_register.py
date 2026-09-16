from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SafetyRegisterEntry(Base):
    """Registre spécial sécurité/santé (Art. L.414-14).

    Constatations du délégué sécurité/santé, consignées dans le registre au
    bureau de l'entreprise, contresignées par le chef de service.

    Intégrité (v2026.09.004) : toute création / contreseing / annulation est
    journalisée dans SafetyRegisterEvent (chaîne SHA-256 append-only). Une
    entrée n'est JAMAIS supprimée — elle est annulée (voided) avec motif.
    """

    __tablename__ = "safety_register_entries"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    delegate_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date = Column(Date, nullable=False)
    location = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending | countersigned | voided
    chef_service_name = Column(String(200), nullable=True)
    countersigned_at = Column(DateTime(timezone=True), nullable=True)
    # Annulation (remplace l'ancienne suppression définitive)
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    void_reason = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization")
    delegate = relationship("User", foreign_keys=[delegate_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    voided_by = relationship("User", foreign_keys=[voided_by_id])


class SafetyRegisterEvent(Base):
    """Événement append-only du registre — maillon de la chaîne d'intégrité.

    Chaque événement (create / countersign / void) est haché :
        event_hash = sha256_hex(prev_hash + "|" + payload_json)
    où prev_hash est le hash de l'événement précédent de la MÊME organisation
    ("0"*64 pour le premier) et payload_json les octets UTF-8 exacts stockés.
    Modifier ou supprimer un événement casse la chaîne — détectable par
    recalcul (voir app/services/register_chain.py et la page /verify).
    """

    __tablename__ = "safety_register_events"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    entry_id = Column(Integer, ForeignKey("safety_register_entries.id"), nullable=True)
    action = Column(String(20), nullable=False)  # create | countersign | void
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(200), nullable=True)
    at = Column(DateTime(timezone=True), nullable=False)
    payload_json = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)

    organization = relationship("Organization")


class SafetyRegisterSeal(Base):
    """Sceau périodique du registre (preuve externe de non-modification).

    Fige {event_count, head_hash} à un instant donné, avec :
    - manifest : texte exact horodaté (RFC 3161) par une autorité d'horodatage ;
    - tsa_token_b64 : jeton d'horodatage RFC 3161 (vérifiable via openssl) ;
    - email de notification au bureau (copie externe du sceau).
    """

    __tablename__ = "safety_register_seals"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    sealed_at = Column(DateTime(timezone=True), nullable=False)
    event_count = Column(Integer, nullable=False)
    head_hash = Column(String(64), nullable=False)
    manifest = Column(Text, nullable=False)
    tsa_status = Column(String(20), nullable=False, default="none")  # ok | failed | unavailable | disabled | none
    tsa_url = Column(String(300), nullable=True)
    tsa_token_b64 = Column(Text, nullable=True)
    auto = Column(Boolean, nullable=False, default=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization")
    created_by = relationship("User")
