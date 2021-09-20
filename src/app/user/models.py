from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    sql,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class User(Base):
    __tablename__ = "user_user"

    id = Column(Integer, primary_key=True, index=True, unique=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    first_name = Column(String(150))
    last_name = Column(String(150))
    date_join = Column(DateTime(timezone=True), server_default=sql.func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    avatar = Column(String)


class SocialAccount(Base):
    __tablename__ = "user_social_account"

    id = Column(Integer, primary_key=True, index=True, unique=True)
    account_id = Column(Integer)
    account_url = Column(String)
    account_login = Column(String)
    account_name = Column(String)
    provider = Column(String)

    user_id = Column(Integer, ForeignKey('user_user.id', ondelete='CASCADE'))
    user = relationship("User", backref='social_account')
