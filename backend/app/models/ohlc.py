"""
OHLCDaily — zilnic Open/High/Low/Close/Volume pentru companii listate la BVB.

Constrângeri:
  - Valorile monetare sunt Numeric(14, 4), niciodată float.
  - Upsert idempotent prin constrângerea unică uq_ohlc_ticker_date.
  - Indecșii sunt proiectați pentru query rapid pe (ticker, trade_date DESC).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OHLCDaily(Base):
    __tablename__ = "ohlc_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Ticker BVB, ex: "TLV", "SNP", "FP" — uppercase, max 16 caractere
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    # OHLC — Numeric(14,4) respectă constrângerea hard #1/#15 din proiect
    open:  Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    high:  Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    low:   Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))

    # Volum — 0 ca default pentru zilele fără tranzacții
    volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    __table_args__ = (
        # Upsert ON CONFLICT pe această constrângere
        UniqueConstraint("ticker", "trade_date", name="uq_ohlc_ticker_date"),
        # Index descendent pentru query-ul principal: ticker + date range, ordonat recent-first
        Index("ix_ohlc_ticker_date_desc", "ticker", "trade_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<OHLCDaily {self.ticker} {self.trade_date} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume}>"
        )
