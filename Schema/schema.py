from pydantic import BaseModel, EmailStr, constr, Field, validator 
from datetime import date
from enum import Enum

class ContactBase(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=50) 
    email: EmailStr 
    company : constr(min_length=1, max_length=50)
    message :  constr(strip_whitespace=True, min_length=1, max_length=200)
    subject :  constr(min_length=1, max_length=50)
    phone :  constr(strip_whitespace=True, min_length=10, max_length=10) 


class UserBase(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=50) 
    email: EmailStr 
    password: constr(min_length=6) 
    aadhar: constr(min_length=12, max_length=12, pattern=r'^\d{12}$') 
    birth_date:date 
    @validator("birth_date")
    def check_birth_date(cls, v):
        if v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v


class User2Base(BaseModel): 
    name: str 
    email: EmailStr 
    aadhar: str 
    birth_date: date 
    balance: float


class Login(BaseModel):
    email: EmailStr 
    password: str

class OrderBase(BaseModel): 
    sid: str 
    quantity: int = Field(default=1)
    price : float

class BalanceUpdate(BaseModel):
    balance: float
 
class SellRequest(BaseModel):
    sid:str
    quantity:int
    price:float

class OrderType(str,Enum):
    BUY = "BUY"
    SELL = "SELL"



class ShareBase(BaseModel): 
    sid: int 
    name: constr(strip_whitespace=True, min_length=2, max_length=50) 
    price: float = Field(gt=0)
    prev_price:float = Field(gt=0)
    description: constr(min_length=10, max_length=500)
