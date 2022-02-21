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
    UserId = sqlalchemy.Column(Integer)
    NeighbourhoodId = sqlalchemy.Column(
        Integer, ForeignKey("Neighbourhoods.Id"))
    Neighbourhood = relationship("Neighbourhood", back_populates="Reports")


class User(Base):
    """The users table model"""
    __tablename__ = "Users"
    Id = sqlalchemy.Column(Integer, primary_key=True)
    LastLocationId = sqlalchemy.Column(Integer)
    Settings = sqlalchemy.Column(String)
    LastInteraction = sqlalchemy.Column(DateTime)
    GoogleId = sqlalchemy.Column(String)
    SessionId = sqlalchemy.Column(String)
    LastLocationId = sqlalchemy.Column(
        Integer, ForeignKey("Neighbourhoods.Id"))
    LastLocation = relationship("Neighbourhood", back_populates="Users")


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
    Ratio = sqlalchemy.Column(Float)
    HasChilds = sqlalchemy.Column(Boolean)
    LiveCount = sqlalchemy.Column(Integer)
    Name = sqlalchemy.Column(String)
    OSMId = sqlalchemy.Column(String)
    IsRelation = sqlalchemy.Column(Boolean)
    IsBig = sqlalchemy.Column(Boolean)
    Users = relationship("User", back_populates="LastLocation")
    Reports = relationship("Report", back_populates="Neighbourhood")
    # Parents = relationship("Neighbourhood", back_populates="Childs",
    #    secondary="ChildParents", foreign_keys=ChildParents.ParentsId)
    Childs = relationship("Neighbourhood", backref="Parents",
                          secondary="ChildParents", primaryjoin=Id == ChildParents.ParentsId,
                          secondaryjoin=Id == ChildParents.ChildsId)
