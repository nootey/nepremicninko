import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    MetaData,
    Float,
    func,
    Enum, Boolean,
)
from sqlalchemy.orm import declarative_base, Mapped

meta = MetaData()
Base = declarative_base(metadata=meta)


class ListingType(str, enum.Enum):
    selling = "selling"
    renting = "renting"


class Listing(Base):
    __tablename__ = "listing"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = Column(String(50), unique=True, index=True)
    url: Mapped[str] = Column(String(150), unique=True)
    listing_type: Mapped[ListingType] = Column(Enum(ListingType))
    location: Mapped[Optional[str]] = Column(String(200), nullable=True)

    # Price tracking
    price: Mapped[float] = Column(Float)
    last_price: Mapped[Optional[float]] = Column(Float, nullable=True)
    is_price_per_sqm: Mapped[bool] = Column(Boolean, default=False)

    # Timestamps
    first_seen: Mapped[datetime] = Column(DateTime, default=func.now())
    last_seen: Mapped[datetime] = Column(DateTime, default=func.now(), onupdate=func.now())
    accessed_time: Mapped[datetime] = Column(DateTime)

    def __repr__(self):
        return f"<Listing(id={self.item_id}, price={self.price}, type={self.listing_type.value})>"