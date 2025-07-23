from sqlalchemy import Column, ForeignKey, Integer, String, Date, Float,DateTime
from Database.database import Base
from sqlalchemy.orm import relationship
from datetime import date, datetime
import enum 
from sqlalchemy import Enum

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True,index=True)
    name = Column(String(50),nullable=False)
    email = Column(String(50),nullable=False,unique=True)
    password = Column(String(300),nullable=False)
    aadhar = Column(String(12),nullable=False)
    birth_date = Column(Date,nullable=False)
    balance = Column(Float,default = 10000)

    orders = relationship("Order",back_populates="user")

class Contact(Base):
    __tablename__ = 'contact'

    id=Column(Integer,primary_key=True,index=True)
    name = Column(String(20),nullable=False)
    company = Column(String(50),nullable=False)
    email = Column(String(20),nullable=False)
    message = Column(String(200),nullable=False)
    phone = Column(String(10),nullable=False)
    subject = Column(String(50),nullable=False)

class OrderType(str,enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Order(Base):
    __tablename__ = 'order'

    oid = Column(Integer, primary_key=True,index=True)
    order_date = Column(Date,nullable=False)
    sid = Column(String(50),ForeignKey('shares.sid'))
    uid = Column(Integer, ForeignKey('user.id'))
    quantity = Column(Integer,nullable=False,default=1)
    Otype = Column(Enum(OrderType),nullable=False)
    price = Column(Float,nullable=False)

    user = relationship("User", back_populates="orders")
    share = relationship("Shares", back_populates="order")



class Shares(Base):
    __tablename__ = 'shares'

    sid = Column(String(50), primary_key=True)
    name = Column(String(50),nullable=False)
    price = Column(Float,nullable=False)
    prev_price = Column(Float)
    description = Column(String(500),nullable=False)

    order = relationship("Order",back_populates="share")



class SharePrices(Base):
    __tablename__ = 'shareprice'

    id = Column(Integer,primary_key=True,index=True)
    share_id = Column(Integer,ForeignKey("shares.sid"),nullable=False)
    price = Column(Float,nullable=False)
    timeStamp = Column(DateTime,default=datetime.utcnow)