from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from app.db.database import Base


class JsonList(TypeDecorator):
    """Serialises a list of strings as JSONB on PostgreSQL, plain JSON on SQLite/others.

    This makes the column usable in both production PostgreSQL and SQLite-backed
    test suites without dialect-specific code in the application layer.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return list(value) if value is not None else []

    def process_result_value(self, value, dialect):
        return list(value) if value is not None else []


class UserBusiness(Base):
    __tablename__ = "user_business"

    id              = Column(Integer, primary_key=True, nullable=False)
    name            = Column(String, nullable=False)
    user_name       = Column(String, nullable=False, unique=True)
    business_name   = Column(String, nullable=False)
    email           = Column(String, nullable=False, unique=True)
    seo_keyword     = Column(JsonList, nullable=False, default=list)
    mobile_no       = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=True)
    review_link     = Column(String, nullable=False, default="")
    business_desc   = Column(Text,   nullable=False, default="")
    qr_code_url     = Column(String, nullable=True)
    google_id       = Column(String, nullable=True, unique=True)
    google_place_id = Column(String, nullable=True)
    auth_provider   = Column(String, nullable=False, default="local")

    # User preferences stored with the account
    language   = Column(String, nullable=False, default="English",      server_default="English")
    tone       = Column(String, nullable=False, default="Professional",  server_default="Professional")
    bill_items = Column(Text,   nullable=False, default="",             server_default="")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    reviews = relationship(
        "GeneratedReview", back_populates="user", cascade="all, delete-orphan"
    )


class GeneratedReview(Base):
    __tablename__ = "generated_reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_generated_reviews_rating"),
    )

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("user_business.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    rating        = Column(Integer, nullable=False)
    review_text   = Column(Text, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user = relationship("UserBusiness", back_populates="reviews")
