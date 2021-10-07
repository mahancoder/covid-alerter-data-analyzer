from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, String, Numeric
import sqlalchemy, sqlalchemy.orm
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base 

Base = declarative_base()

class Report(Base):
    __tablename__ = "Reports"
    Id = sqlalchemy.Column(Integer, primary_key=True)
    Longitude = sqlalchemy.Column(Numeric)
    Latitude = sqlalchemy.Column(Numeric)
    UserId = sqlalchemy.Column(Integer)
    NeighbourhoodId = sqlalchemy.Column(Integer, ForeignKey("Neighbourhoods.Id"))
    Neighbourhood = relationship("Neighbourhood", back_populates="Reports")
class User(Base):
    __tablename__ = "Users"
    Id = sqlalchemy.Column(Integer, primary_key=True)
    LastLocationId = sqlalchemy.Column(Integer)
    Settings = sqlalchemy.Column(String)
    LastInteraction = sqlalchemy.Column(DateTime)
    GoogleId = sqlalchemy.Column(String)
    SessionId = sqlalchemy.Column(String)
    LastLocationId = sqlalchemy.Column(Integer, ForeignKey("Neighbourhoods.Id"))
    LastLocation = relationship("Neighbourhood", back_populates="Users")
class Neighbourhood(Base):
    __tablename__ = "Neighbourhoods"
    Id = sqlalchemy.Column(Integer, primary_key=True)
    Ratio = sqlalchemy.Column(Integer)
    HasChilds= sqlalchemy.Column(Boolean)
    LiveCount = sqlalchemy.Column(Integer)
    Name = sqlalchemy.Column(String)
    OSMId = sqlalchemy.Column(String)
    OSMType = sqlalchemy.Column(String)
    Users = relationship("User", back_populates="LastLocation")
    Reports = relationship("Report", back_populates="Neighbourhood")