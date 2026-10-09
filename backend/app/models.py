"""Database models.

Off-chain data (proposal text, demographics) lives in `proposals`.
The tamper-evident ledger lives in `ledger_blocks`: each block stores only the
content hash, category and timestamp, chained to the previous block's hash.
`anchors` records Merkle roots of block ranges that can be written to a public
blockchain (see contracts/ProposalRegistry.sol).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Consultation(Base):
    """A draft law or policy topic opened for youth input."""
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    law_reference: Mapped[str] = mapped_column(String(300), default="")
    organizer: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    proposals: Mapped[list["Proposal"]] = relationship(back_populates="consultation")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultation_id: Mapped[int | None] = mapped_column(ForeignKey("consultations.id"), nullable=True, index=True)
    # NULL after the author exercises the right to erasure; the hash stays on the ledger.
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_group: Mapped[str] = mapped_column(String(20), default="")
    location: Mapped[str] = mapped_column(String(60), default="")
    category: Mapped[str] = mapped_column(String(60), index=True)
    sentiment: Mapped[str] = mapped_column(String(30))
    urgency: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    classifier: Mapped[str] = mapped_column(String(30), default="rules")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    # received | reviewed | reflected | not_reflected
    status: Mapped[str] = mapped_column(String(20), default="received", index=True)
    response_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    erased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SHA-256 of a one-time secret given only to the author; needed to erase the proposal.
    owner_secret_hash: Mapped[str] = mapped_column(String(64), default="")

    consultation: Mapped[Consultation | None] = relationship(back_populates="proposals")
    block: Mapped["LedgerBlock"] = relationship(back_populates="proposal", uselist=False)


class LedgerBlock(Base):
    __tablename__ = "ledger_blocks"

    index: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    timestamp: Mapped[str] = mapped_column(String(40))  # ISO-8601 string, hashed verbatim
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"), unique=True)
    category: Mapped[str] = mapped_column(String(60))
    content_hash: Mapped[str] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64))
    block_hash: Mapped[str] = mapped_column(String(64), unique=True)

    proposal: Mapped[Proposal] = relationship(back_populates="block")


class Anchor(Base):
    """Merkle root of a range of ledger blocks, optionally published on-chain."""
    __tablename__ = "anchors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_index: Mapped[int] = mapped_column(Integer)
    to_index: Mapped[int] = mapped_column(Integer)
    merkle_root: Mapped[str] = mapped_column(String(64))
    network: Mapped[str] = mapped_column(String(40), default="local")
    tx_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
