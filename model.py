"""The database model"""
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, String, Numeric, Float
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Report(Base):
    """The reports table model"""
    __tablename__ = "Reports"
    Id = sqlalchemy.Column(Integer, primary_key=True)
    Longitude = sqlalchemy.Column(Numeric)
    Latitude = sqlalchemy.Column(Numeric)

    # The user who created the report
    UserId = sqlalchemy.Column(Integer, ForeignKey("Users.Id"))
    User = relationship("User", back_populates="Reports")

    # The neighbourhood in which the report was sent
    NeighbourhoodId = sqlalchemy.Column(
        Integer, ForeignKey("Neighbourhoods.Id"))
    Neighbourhood = relationship("Neighbourhood", back_populates="Reports")

    # The timestamp when the report was sent
    Timestamp = sqlalchemy.Column(DateTime)


class User(Base):
    """The users table model"""
    __tablename__ = "Users"
    Id = sqlalchemy.Column(Integer, primary_key=True)

    # The user settings
    Settings = sqlalchemy.Column(String)

    # The user last interaction time (used to expire the tokens)
    LastInteraction = sqlalchemy.Column(DateTime)

    # The user's Google Account Id
    GoogleId = sqlalchemy.Column(String)

    SessionId = sqlalchemy.Column(String)

    # The user's last neighbourhood (used for live count)
    LastLocationId = sqlalchemy.Column(
        Integer, ForeignKey("Neighbourhoods.Id"))
    LastLocation = relationship("Neighbourhood", back_populates="Users")

    # A list of user's reports
    Reports = relationship("Report", back_populates="User")


class ChildParents(Base):
    """The neighbourhood childs and parents relationship table"""
    __tablename__ = "ChildParents"
    Id = sqlalchemy.Column(Integer, primary_key=True, autoincrement=True)
    ParentsId = sqlalchemy.Column(Integer, ForeignKey("Neighbourhoods.Id"))
    ChildsId = sqlalchemy.Column(Integer, ForeignKey("Neighbourhoods.Id"))


class Neighbourhood(Base):
    """The neighbourhoods table model"""
    __tablename__ = "Neighbourhoods"
    Id = sqlalchemy.Column(Integer, primary_key=True, autoincrement=True)

    # The neighbourhood PAR
    Ratio = sqlalchemy.Column(Float)

    # Whether the neighbourhood has child neighbourhoods
    HasChilds = sqlalchemy.Column(Boolean)

    # The neighbourhood's live count
    LiveCount = sqlalchemy.Column(Integer)

    Name = sqlalchemy.Column(String)
    OSMId = sqlalchemy.Column(String)

    # Whether the neighbourhood is a relation (OSM type)
    IsRelation = sqlalchemy.Column(Boolean)

    # Whether the area is a neighbourhood or something big like province
    IsBig = sqlalchemy.Column(Boolean)

    # Users which are currently inside the neighbourhood
    Users = relationship("User", back_populates="LastLocation")

    # Reports which were sent in the neighbourhood
    Reports = relationship("Report", back_populates="Neighbourhood")

    # The child neighbourhoods
    Childs = relationship("Neighbourhood", backref="Parents",
                          secondary="ChildParents", primaryjoin=Id == ChildParents.ParentsId,
                          secondaryjoin=Id == ChildParents.ChildsId)
class ScoreLog(Base):
    """The score log table model"""
    __tablename__ = "ScoreLogs"
    Id = sqlalchemy.Column(Integer, primary_key=True, autoincrement=True)
    NeighbourhoodId = sqlalchemy.Column(Integer, ForeignKey("Neighbourhoods.Id"))
    Neighbourhood = relationship("Neighbourhood", backref="ScoreLogs")
    Score = sqlalchemy.Column(Float)
    Date = sqlalchemy.Column(DateTime)
