"""Database EmailVerificationToken repository implementation."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import select

from domain.repositories.email_verification_token_repository import EmailVerificationTokenRepository
from domain.entities.email_verification_token import EmailVerificationToken
from infrastructure.database.models import EmailVerificationToken as EmailVerificationTokenModel
from infrastructure.database.adapter import db_adapter


def _model_to_entity(m: EmailVerificationTokenModel) -> EmailVerificationToken:
    return EmailVerificationToken(
        id=str(m.id),
        user_id=str(m.user_id),
        token_hash=m.token_hash or "",
        created_at=m.created_at,
        expires_at=m.expires_at,
        used_at=m.used_at,
    )


class DatabaseEmailVerificationTokenRepository(EmailVerificationTokenRepository):
    """PostgreSQL implementation of EmailVerificationTokenRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            model = EmailVerificationTokenModel(
                user_id=UUID(token.user_id),
                token_hash=token.token_hash,
                created_at=token.created_at,
                expires_at=token.expires_at,
                used_at=token.used_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def get_by_token_hash(self, token_hash: str) -> Optional[EmailVerificationToken]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(EmailVerificationTokenModel).where(
                    EmailVerificationTokenModel.token_hash == token_hash,
                    EmailVerificationTokenModel.used_at.is_(None),
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def update(self, token: EmailVerificationToken) -> EmailVerificationToken:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(EmailVerificationTokenModel).where(
                    EmailVerificationTokenModel.id == UUID(token.id)
                )
            )
            m = r.scalar_one_or_none()
            if not m:
                raise ValueError("EmailVerificationToken not found")
            m.used_at = token.used_at
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)
