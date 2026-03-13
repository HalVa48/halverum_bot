import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    configs: Mapped[list["UserConfig"]] = relationship(
        "UserConfig", back_populates="user", cascade="all, delete-orphan"
    )


class UserConfig(Base):
    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="configs")
