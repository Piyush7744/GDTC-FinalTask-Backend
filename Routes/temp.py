from fastapi import FastAPI, HTTPException, Depends, status,APIRouter
from pydantic import BaseModel,EmailStr, constr, Field, validator
from typing import Annotated, Optional
from Models import models
from Database.database import engine,SessionLocal
from sqlalchemy.orm import Session
from datetime import date 


models.Base.metadata.create_all(bind=engine)

def get_db():
    db=SessionLocal()

    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session,Depends(get_db)]

class UserBase(BaseModel):
    id: int
    name: constr(strip_whitespace=True, min_length=1, max_length=50)
    email: EmailStr
    password: constr(min_length=6)
    aadhar: constr(min_length=12, max_length=12, pattern=r'^\d{12}$')
    birth_date: date
    balance:float = 10000;
 
    @validator("birth_date")
    def check_birth_date(cls, v):
        if v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v
 
#  I have created this for reponse model
class User2Base(BaseModel):
    id: int
    name: constr(strip_whitespace=True, min_length=1, max_length=50)
    email: EmailStr
    aadhar: constr(min_length=12, max_length=12, pattern=r'^\d{12}$')
    birth_date: date
    balance:float


class Login(BaseModel):
    email:EmailStr
    password:str

class ShareBase(BaseModel):
    sid: int
    name: constr(strip_whitespace=True, min_length=2, max_length=50)
    price: float = Field(gt=0, description="Price must be greater than 0")
    description: constr(min_length=10, max_length=500)
 
class OrderBase(BaseModel):
    oid: int
    order_date: Optional[date] = None  # auto-filled later
    sid: int
    uid: int
    quantity:int = Field(default = 1)

router = APIRouter()


# All the post methods 
@router.post("/register",status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase,db:db_dependency):
    db_user = models.User(id=user.id, name=user.name, email=user.email,password=user.password,aadhar=user.aadhar,birth_date=user.birth_date)
    db.add(db_user)
    db.commit()


@router.post("/login",status_code=status.HTTP_200_OK)
async def login(request:Login,db:db_dependency):
    user = db.query(models.User).filter(models.User.email==request.email).first()

    if not user or user.password!=request.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid username or password")

    return {
        "message":"Login successfull",
        "User_id":user.id,
        "name":user.name,
        "Email":user.email
    }

@router.post("/shares",status_code=status.HTTP_201_CREATED)
async def create_share(share: ShareBase,db:db_dependency):
    db_product = models.Shares(sid=share.sid, name=share.name, price=share.price,description=share.description)
    db.add(db_product)
    db.commit()

@router.post("/order",status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderBase,db:db_dependency):

    # here i am checking if user or share exist or not
    user = db.query(models.User).filter(models.User.id == order.uid).first()
    share = db.query(models.Shares).filter(models.Shares.sid == order.sid).first()

    if not user or not share:
        raise HTTPException(status_code=404,detail="User or share not found")
    db_order = models.Order(oid=order.oid,order_date=date.today(),sid=order.sid, uid=order.uid,quantity = order.quantity)
    db.add(db_order)
    db.commit()






#All Get methods
@router.get("/user/{user_id}",status_code=status.HTTP_200_OK,response_model = User2Base)
async def get_customer(user_id:int,db:db_dependency):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Customer not found")
    return user


@router.get("/share/{sid}",status_code=status.HTTP_200_OK)
async def get_product(sid:int,db:db_dependency):
    share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    return share


@router.get("/shares/",status_code=status.HTTP_200_OK)
async def get_product(db:db_dependency):
    shares = db.query(models.Shares).all()
    if shares is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    return share



@router.get("/order/{order_id}")
def get_order_details(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.oid == order_id).first()
    if order is None:
        return {"error": "Order not found"}

    return {
        "order_id": order.oid,
        "order_date":order.order_date,
        "user": {
            "id": order.user.id,
            "name": order.user.name,
            "email": order.user.email,
            "aadhar": order.user.aadhar,
            "birth_date": order.user.birth_date,
            "balance":order.balance
        },
        "shares": {
            "id": order.share.sid,
            "name": order.share.name,
            "price": order.share.price,
            "description": order.share.description
        }
    }


@router.get("/userShares/{uid}",status_code=status.HTTP_200_OK)
async def get_user_shares(uid:int,db:db_dependency):
    orders = db.query(models.Order).filter(models.Order.uid == uid).all()
    if orders is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User dont have shares")

    shares_list = []
    for order in orders:
        share = order.share
        shares_list.append({
            "oid":order.oid,
            "order_date":order.order_date,
            "sid":share.sid,
            "name":share.name,
            "price":share.price,
            "description":share.description,
            "quantity":order.quantity,
            "total":order.quantity * share.price,
        }
        )

    return {"user_id":uid,"purchased_shares":shares_list}





#All put methods
@router.put("/user/{uid}",status_code=status.HTTP_204_NO_CONTENT)
async def update_customer(uid: int,user:UserBase,db:db_dependency):
    db_user = db.query(models.User).filter(models.User.id == uid).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Customer not found")
    db_user.id = user.id
    db_user.name = user.name
    db_user.email = user.email
    db_user.password = user.password
    db_user.aadhar = user.aadhar
    db_user.birth_date = user.birth_date
    db_user.balance = user.balance
    db.add(db_user)
    db.commit()
    return user

@router.put("/share/{sid}",status_code=status.HTTP_204_NO_CONTENT)
async def update_product(sid: int,share:ShareBase,db:db_dependency):
    db_share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
    if db_share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    db_share.pid = share.sid
    db_share.name = share.name
    db_share.price = share.price
    db_share.description = share.description
    db.add(db_share)
    db.commit()
    return db_share




# All delete methods
@router.delete("/user/{uid}")
async def delete_user(uid:int,db:db_dependency):
    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Customer not found")
    db.delete(user)
    db.commit()

@router.delete("/share/{sid}")
async def delete_product(sid:int,db:db_dependency):
    share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    db.delete(share)
    db.commit()
