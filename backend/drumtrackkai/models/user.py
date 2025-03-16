from .. import db
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class SubscriptionTier(PyEnum):
    FREE = 'free'
    INDIVIDUAL = 'individual'
    PROFESSIONAL = 'professional'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    subscription_tier = db.Column(
        db.Enum(SubscriptionTier),
        default=SubscriptionTier.FREE
    )

    credits_remaining = db.Column(db.Integer, default=3)
    total_analyses = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)