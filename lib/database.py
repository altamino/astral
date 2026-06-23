from sqlalchemy import create_engine, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from .config import Config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    lang: Mapped[str] = mapped_column(String(7))


_engine = create_engine(f"sqlite:///{Config.LOCAL_DB}")
Base.metadata.create_all(_engine)


class UserManager:
    def __init__(self):
        self.engine = _engine

    def get(self, uid: str) -> User:
        with Session(self.engine) as session:
            stmt = select(User).where(User.id == uid)
            u = session.execute(stmt).scalar_one_or_none()

            if not u:
                u = User(id=uid, lang="en")
                session.add(u)
                session.commit()
                session.refresh(u)
            return u

    def update(self, uid: str, lang: str = None):
        with Session(self.engine) as session:
            u = session.get(User, uid)
            if u:
                if lang is not None:
                    u.lang = lang
                session.commit()
                return True
            return False
