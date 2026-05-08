from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserBusiness(Base):
    __tablename__ = "user_business"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    user_name = Column(String, nullable=False, unique=True)
    business_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    seo_keyword = Column(ARRAY(String), nullable=False, default=list)
    mobile_no = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=True)
    review_link = Column(String, nullable=False, default="")
    business_desc = Column(Text, nullable=False, default="")
    qr_code_url = Column(String, nullable=True)
    google_id = Column(String, nullable=True, unique=True)                                                                                               
    google_place_id = Column(String, nullable=True)
    auth_provider = Column(String, nullable=False, default="local")

    reviews = relationship(
        "GeneratedReview", back_populates="user", cascade="all, delete-orphan"
    )


class GeneratedReview(Base):
    __tablename__ = "generated_reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_business.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserBusiness", back_populates="reviews")
