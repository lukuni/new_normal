"""Tamper-evident hash-chain ledger and Merkle anchoring.

content_hash = SHA-256(proposal text)
block_hash   = SHA-256(index | timestamp | category | content_hash | prev_hash)

Changing a stored proposal changes its content hash; changing a block field
changes its block hash; deleting or reordering blocks breaks prev_hash links.
`verify_chain` detects all three.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Anchor, LedgerBlock, Proposal

GENESIS = "0" * 64


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def block_hash(index: int, timestamp: str, category: str, content_hash: str, prev_hash: str) -> str:
    return sha256(f"{index}|{timestamp}|{category}|{content_hash}|{prev_hash}")


def append_block(db: Session, proposal: Proposal, at: datetime | None = None) -> LedgerBlock:
    """Append a block for `proposal`. Caller commits."""
    last = db.execute(select(LedgerBlock).order_by(LedgerBlock.index.desc()).limit(1)).scalar_one_or_none()
    index = 0 if last is None else last.index + 1
    prev = GENESIS if last is None else last.block_hash
    ts = (at or datetime.now(timezone.utc)).isoformat(timespec="milliseconds")
    blk = LedgerBlock(index=index, timestamp=ts, proposal_id=proposal.id, category=proposal.category,
                      content_hash=proposal.content_hash, prev_hash=prev,
                      block_hash=block_hash(index, ts, proposal.category, proposal.content_hash, prev))
    db.add(blk)
    return blk


def verify_chain(db: Session) -> dict:
    """Check every block. Returns {'ok', 'checked', 'issues': [...], 'erased': n}."""
    blocks = db.execute(select(LedgerBlock).order_by(LedgerBlock.index)).scalars().all()
    issues, erased, prev = [], 0, GENESIS
    for expected_index, b in enumerate(blocks):
        problems = []
        if b.index != expected_index:
            problems.append("missing_block_before")
        if b.prev_hash != prev:
            problems.append("broken_link")
        if block_hash(b.index, b.timestamp, b.category, b.content_hash, b.prev_hash) != b.block_hash:
            problems.append("block_modified")
        p = b.proposal
        if p is None:
            problems.append("proposal_missing")
        elif p.text is None:
            erased += 1  # lawful erasure: text removed, hash kept - not an integrity failure
        elif sha256(p.text) != b.content_hash:
            problems.append("content_modified")
        if problems:
            issues.append({"index": b.index, "proposal_id": b.proposal_id, "problems": problems})
        prev = b.block_hash
    return {"ok": not issues, "checked": len(blocks), "issues": issues, "erased": erased}


# ---------------- Merkle tree (for batching many blocks into one on-chain tx) ----------------

def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return GENESIS
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [sha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_proof(leaves: list[str], idx: int) -> list[dict]:
    """Sibling path proving leaves[idx] is in the tree."""
    proof, level, i = [], list(leaves), idx
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = i ^ 1
        proof.append({"hash": level[sib], "position": "left" if sib < i else "right"})
        level = [sha256(level[k] + level[k + 1]) for k in range(0, len(level), 2)]
        i //= 2
    return proof


def verify_merkle_proof(leaf: str, proof: list[dict], root: str) -> bool:
    h = leaf
    for step in proof:
        h = sha256(step["hash"] + h) if step["position"] == "left" else sha256(h + step["hash"])
    return h == root


def create_anchor(db: Session, network: str = "local") -> Anchor | None:
    """Anchor all blocks not yet covered by a previous anchor. Caller commits."""
    last_to = db.execute(select(func.max(Anchor.to_index))).scalar()
    start = 0 if last_to is None else last_to + 1
    blocks = db.execute(select(LedgerBlock).where(LedgerBlock.index >= start)
                        .order_by(LedgerBlock.index)).scalars().all()
    if not blocks:
        return None
    a = Anchor(from_index=blocks[0].index, to_index=blocks[-1].index,
               merkle_root=merkle_root([b.block_hash for b in blocks]), network=network)
    db.add(a)
    return a
