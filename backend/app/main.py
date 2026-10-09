"""Залуу Дуу Хоолой - REST API.

Public:  submit proposals, check receipts, read stats/ledger/brief, request erasure.
Admin:   manage consultations, respond to proposals, anchor ledger (X-Admin-Token).
Demo:    tamper/restore endpoints for live presentations (DEMO_MODE=true).
"""
from __future__ import annotations

import secrets
import threading
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ledger
from .brief import build_brief
from .config import settings
from .db import Base, SessionLocal, engine, get_db
from .models import Anchor, Consultation, LedgerBlock, Proposal
from .nlp import CATEGORIES, get_classifier, scrub_pii
from .schemas import (AGE_GROUPS, STATUSES, AdminUpdate, ConsultationIn, ConsultationOut, EraseIn,
                      ProposalIn, ProposalOut, ReceiptOut, ReceiptStatus)
from .seed import seed

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_on_start:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="Залуу Дуу Хоолой API", version="1.0.0", lifespan=lifespan,
              description="Залуучуудын бодлогын саналыг цуглуулах, ангилах, блокчейн-маягийн бүртгэлээр баталгаажуулах платформ.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

# Serialises ledger appends inside one process; the DB primary key on block index
# protects against concurrent writers across processes.
_ledger_lock = threading.Lock()
_tamper_backup: dict[int, str] = {}


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Админ токен буруу")


def _proposal_out(p: Proposal) -> ProposalOut:
    out = ProposalOut.model_validate(p)
    out.erased = p.text is None
    return out


# ------------------------------------------------------------------ meta
@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, "classifier": get_classifier().name,
            "blocks": db.execute(select(func.count(LedgerBlock.index))).scalar(),
            "demo_mode": settings.demo_mode}


@app.get("/api/meta")
def meta():
    return {"categories": CATEGORIES, "age_groups": AGE_GROUPS, "statuses": STATUSES,
            "locations": ["Улаанбаатар", "Дархан-Уул", "Орхон", "Хөвсгөл", "Баян-Өлгий", "Бусад аймаг"]}


# ------------------------------------------------------------------ consultations
@app.get("/api/consultations", response_model=list[ConsultationOut])
def list_consultations(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Proposal.consultation_id, func.count(Proposal.id))
                             .group_by(Proposal.consultation_id)).all())
    out = []
    for c in db.execute(select(Consultation).order_by(Consultation.created_at.desc())).scalars():
        o = ConsultationOut.model_validate(c)
        o.proposal_count = counts.get(c.id, 0)
        out.append(o)
    return out


@app.post("/api/consultations", response_model=ConsultationOut, dependencies=[Depends(require_admin)])
def create_consultation(body: ConsultationIn, db: Session = Depends(get_db)):
    c = Consultation(**body.model_dump())
    db.add(c)
    db.commit()
    return ConsultationOut.model_validate(c)


@app.post("/api/consultations/{cid}/close", dependencies=[Depends(require_admin)])
def close_consultation(cid: int, db: Session = Depends(get_db)):
    c = db.get(Consultation, cid) or _404()
    c.status = "closed"
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ proposals
@app.post("/api/proposals", response_model=ReceiptOut, status_code=201)
def submit_proposal(body: ProposalIn, db: Session = Depends(get_db)):
    if body.age_group not in AGE_GROUPS:
        raise HTTPException(422, "Насны бүлэг буруу")
    if body.consultation_id is not None:
        c = db.get(Consultation, body.consultation_id)
        if not c:
            raise HTTPException(404, "Хэлэлцүүлэг олдсонгүй")
        if c.status != "open":
            raise HTTPException(409, "Хэлэлцүүлэг хаагдсан")
    text = scrub_pii(body.text.strip())
    r = get_classifier().classify(text)
    secret = secrets.token_urlsafe(18)
    with _ledger_lock:
        p = Proposal(consultation_id=body.consultation_id, text=text, age_group=body.age_group,
                     location=body.location, category=r.category, sentiment=r.sentiment,
                     urgency=r.urgency, confidence=r.confidence, classifier=r.classifier,
                     content_hash=ledger.sha256(text), owner_secret_hash=ledger.sha256(secret))
        db.add(p)
        db.flush()
        b = ledger.append_block(db, p)
        db.commit()
    return ReceiptOut(proposal_id=p.id, content_hash=p.content_hash, block_index=b.index,
                      block_hash=b.block_hash, prev_hash=b.prev_hash, timestamp=b.timestamp,
                      classification=r.as_dict(), owner_secret=secret)


@app.get("/api/proposals", response_model=list[ProposalOut])
def list_proposals(db: Session = Depends(get_db), category: str | None = None,
                   consultation_id: int | None = None, status: str | None = None,
                   urgency: str | None = None, limit: int = Query(50, le=500), offset: int = 0):
    q = select(Proposal)
    if category:
        q = q.where(Proposal.category == category)
    if consultation_id is not None:
        q = q.where(Proposal.consultation_id == consultation_id)
    if status:
        q = q.where(Proposal.status == status)
    if urgency:
        q = q.where(Proposal.urgency == urgency)
    rows = db.execute(q.order_by(Proposal.created_at.desc()).offset(offset).limit(limit)).scalars()
    return [_proposal_out(p) for p in rows]


@app.get("/api/receipts/{block_hash}", response_model=ReceiptStatus)
def check_receipt(block_hash: str, db: Session = Depends(get_db)):
    """Citizen-facing: look up a proposal by its receipt (block hash) and verify it."""
    b = db.execute(select(LedgerBlock).where(LedgerBlock.block_hash == block_hash.strip().lower())).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Баримт олдсонгүй")
    p = b.proposal
    if p.text is None:
        integrity = "erased"
    else:
        ok = (ledger.sha256(p.text) == b.content_hash and
              ledger.block_hash(b.index, b.timestamp, b.category, b.content_hash, b.prev_hash) == b.block_hash)
        integrity = "intact" if ok else "modified"
    return ReceiptStatus(proposal_id=p.id, status=p.status, response_note=p.response_note, category=p.category,
                         created_at=p.created_at, block_index=b.index, block_hash=b.block_hash, integrity=integrity,
                         consultation_title=p.consultation.title if p.consultation else None)


@app.post("/api/receipts/{block_hash}/erase")
def erase_my_proposal(block_hash: str, body: EraseIn, db: Session = Depends(get_db)):
    """Right to erasure (Хүний хувийн мэдээлэл хамгаалах тухай хууль 16.1.7, 18.2.9):
    the text is deleted off-chain; the hash remains so the ledger stays verifiable."""
    b = db.execute(select(LedgerBlock).where(LedgerBlock.block_hash == block_hash.strip().lower())).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Баримт олдсонгүй")
    p = b.proposal
    if not p.owner_secret_hash or not secrets.compare_digest(p.owner_secret_hash, ledger.sha256(body.owner_secret)):
        raise HTTPException(403, "Нууц код буруу")
    p.text = None
    p.erased_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "message": "Саналын бичвэр устгагдлаа. Бүртгэлийн хэш хэвээр үлдэнэ."}


# ------------------------------------------------------------------ analytics
@app.get("/api/stats")
def stats(db: Session = Depends(get_db), consultation_id: int | None = None):
    q = select(Proposal).where(Proposal.text.is_not(None))
    if consultation_id is not None:
        q = q.where(Proposal.consultation_id == consultation_id)
    ps = db.execute(q).scalars().all()
    n = len(ps)
    count = lambda attr: [{"name": k, "count": v} for k, v in Counter(getattr(p, attr) for p in ps).most_common()]  # noqa: E731
    by_day = Counter(p.created_at.date().isoformat() for p in ps)
    return {
        "total": n,
        "urgent": sum(p.urgency == "Өндөр" for p in ps),
        "reflected": sum(p.status == "reflected" for p in ps),
        "avg_confidence": round(sum(p.confidence for p in ps) / n, 2) if n else 0,
        "by_category": count("category"), "by_sentiment": count("sentiment"),
        "by_location": count("location"), "by_age": count("age_group"),
        "by_status": count("status"), "by_urgency": count("urgency"),
        "by_day": [{"date": d, "count": by_day[d]} for d in sorted(by_day)],
    }


@app.get("/api/brief")
def brief(db: Session = Depends(get_db), consultation_id: int | None = None):
    return build_brief(db, consultation_id)


# ------------------------------------------------------------------ ledger
@app.get("/api/ledger")
def get_ledger(db: Session = Depends(get_db), limit: int = Query(100, le=1000), offset: int = 0):
    total = db.execute(select(func.count(LedgerBlock.index))).scalar()
    rows = db.execute(select(LedgerBlock).order_by(LedgerBlock.index.desc()).offset(offset).limit(limit)).scalars()
    return {"total": total, "blocks": [{
        "index": b.index, "timestamp": b.timestamp, "category": b.category, "content_hash": b.content_hash,
        "prev_hash": b.prev_hash, "block_hash": b.block_hash, "proposal_id": b.proposal_id} for b in rows]}


@app.get("/api/ledger/verify")
def verify(db: Session = Depends(get_db)):
    return ledger.verify_chain(db)


@app.get("/api/anchors")
def list_anchors(db: Session = Depends(get_db)):
    return [{"id": a.id, "from_index": a.from_index, "to_index": a.to_index, "merkle_root": a.merkle_root,
             "network": a.network, "tx_hash": a.tx_hash, "created_at": a.created_at.isoformat()}
            for a in db.execute(select(Anchor).order_by(Anchor.id.desc())).scalars()]


@app.post("/api/anchors", dependencies=[Depends(require_admin)])
def create_anchor(db: Session = Depends(get_db), network: str = "local"):
    a = ledger.create_anchor(db, network)
    if a is None:
        raise HTTPException(409, "Шинэ блок алга")
    db.commit()
    return {"id": a.id, "from_index": a.from_index, "to_index": a.to_index, "merkle_root": a.merkle_root,
            "hint": "Энэ root-ийг contracts/ProposalRegistry.sol-ийн anchor() функцээр сүлжээнд бичнэ."}


@app.patch("/api/anchors/{aid}", dependencies=[Depends(require_admin)])
def set_anchor_tx(aid: int, tx_hash: str, network: str = "sepolia", db: Session = Depends(get_db)):
    a = db.get(Anchor, aid) or _404()
    a.tx_hash, a.network = tx_hash, network
    db.commit()
    return {"ok": True}


@app.get("/api/proofs/{block_hash}")
def merkle_proof(block_hash: str, db: Session = Depends(get_db)):
    """Merkle proof that a block is included in an on-chain anchor."""
    b = db.execute(select(LedgerBlock).where(LedgerBlock.block_hash == block_hash)).scalar_one_or_none() or _404()
    a = db.execute(select(Anchor).where(Anchor.from_index <= b.index, Anchor.to_index >= b.index)).scalar_one_or_none()
    if not a:
        raise HTTPException(409, "Энэ блок хараахан anchor хийгдээгүй")
    leaves = [x.block_hash for x in db.execute(select(LedgerBlock).where(
        LedgerBlock.index.between(a.from_index, a.to_index)).order_by(LedgerBlock.index)).scalars()]
    proof = ledger.merkle_proof(leaves, b.index - a.from_index)
    return {"leaf": b.block_hash, "root": a.merkle_root, "proof": proof, "anchor_id": a.id, "tx_hash": a.tx_hash,
            "valid": ledger.verify_merkle_proof(b.block_hash, proof, a.merkle_root)}


# ------------------------------------------------------------------ admin
@app.patch("/api/admin/proposals/{pid}", response_model=ProposalOut, dependencies=[Depends(require_admin)])
def admin_update(pid: int, body: AdminUpdate, db: Session = Depends(get_db)):
    p = db.get(Proposal, pid) or _404()
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(422, "Төлөв буруу")
        p.status = body.status
    if body.response_note is not None:
        p.response_note = body.response_note
    db.commit()
    return _proposal_out(p)


# ------------------------------------------------------------------ demo (live presentation)
@app.post("/api/demo/tamper/{pid}", dependencies=[Depends(require_admin)])
def demo_tamper(pid: int, db: Session = Depends(get_db)):
    """Simulates an insider silently editing a stored proposal."""
    if not settings.demo_mode:
        raise HTTPException(403, "Demo mode off")
    p = db.get(Proposal, pid) or _404()
    if p.text is None:
        raise HTTPException(409, "Устгагдсан санал")
    _tamper_backup.setdefault(pid, p.text)
    p.text = p.text.replace("өндөр", "бага") if "өндөр" in p.text else p.text + " (засварласан)"
    db.commit()
    return {"ok": True, "message": f"#{pid} саналыг нууцаар засварлалаа. Одоо /api/ledger/verify дуудна уу."}


@app.post("/api/demo/restore", dependencies=[Depends(require_admin)])
def demo_restore(db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(403, "Demo mode off")
    for pid, text in list(_tamper_backup.items()):
        p = db.get(Proposal, pid)
        if p:
            p.text = text
        _tamper_backup.pop(pid)
    db.commit()
    return {"ok": True}


def _404():
    raise HTTPException(404, "Олдсонгүй")
