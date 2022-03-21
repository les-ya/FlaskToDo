import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Doings(SqlAlchemyBase):
    __tablename__ = 'doings'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    content = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    donecheck = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    doing_category = sqlalchemy.Column(sqlalchemy.Boolean)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    user = orm.relation("User", back_populates='doings')