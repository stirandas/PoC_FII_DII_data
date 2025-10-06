# app/models.py
from __future__ import annotations
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Date, Numeric

class Base(DeclarativeBase):
    pass

class TNseFiiDiiEqData(Base):
    __tablename__ = "t_nse_fii_dii_eq_data"

    run_dt: Mapped[date] = mapped_column(Date, primary_key=True)
    dii_buy: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    dii_sell: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    dii_net: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fii_buy: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    fii_sell: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    fii_net: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
