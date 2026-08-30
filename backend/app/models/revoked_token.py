from datetime import datetime
from app import db


class RevokedToken(db.Model):
    """
    Revoked JWT tokens (logout), checked by the token_in_blocklist_loader.

    A DB-backed table rather than an in-process set so revocation actually
    works across gunicorn workers and survives a restart - the in-memory
    set it replaces only revoked a token on whichever single worker
    process happened to handle the logout request.
    """
    __tablename__ = 'revoked_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None

    @classmethod
    def revoke(cls, jti: str, expires_at: datetime):
        db.session.add(cls(jti=jti, expires_at=expires_at))
        db.session.commit()

    @classmethod
    def purge_expired(cls) -> int:
        """
        Delete rows for tokens that have already naturally expired - once a
        token is past its own `exp` claim, flask-jwt-extended rejects it
        regardless of the blocklist, so there's no reason to keep growing
        this table forever. Returns the number of rows removed.
        """
        deleted = cls.query.filter(cls.expires_at < datetime.utcnow()).delete()
        db.session.commit()
        return deleted

    def __repr__(self):
        return f'<RevokedToken {self.jti}>'
