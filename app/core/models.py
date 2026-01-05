import enum
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    MetaData,
    String,
    func,
)
from sqlalchemy.orm import Mapped, declarative_base

meta = MetaData()
Base = declarative_base(metadata=meta)


def get_model_hash() -> str:
    """Generate a hash of the Listing model schema."""
    columns = []
    for column in Listing.__table__.columns:
        columns.append(f"{column.name}:{column.type}")

    schema_string = "|".join(sorted(columns))
    return hashlib.md5(schema_string.encode()).hexdigest()


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

    # Size tracking
    size_sqm: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Timestamps
    first_seen: Mapped[datetime] = Column(DateTime, default=func.now())
    last_seen: Mapped[datetime] = Column(DateTime, default=func.now(), onupdate=func.now())
    accessed_time: Mapped[datetime] = Column(DateTime)

    @property
    def price_per_sqm(self) -> Optional[float]:
        if self.listing_type == ListingType.selling and self.size_sqm and self.size_sqm > 0:
            return round(self.price / self.size_sqm, 2)
        return None

    def __repr__(self):
        return f"<Listing(id={self.item_id}, price={self.price}, type={self.listing_type.value})>"


class ConfigState(Base):
    __tablename__ = "config_state"

    id = Column(Integer, primary_key=True)
    url_hash = Column(String, nullable=True)
    schema_hash = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False)
