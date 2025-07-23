from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from typing import Annotated, Optional 
from Models import models 
from Database.database import engine, SessionLocal 
from sqlalchemy.orm import Session 
from datetime import date,timedelta,datetime
from Auth.auth import oauth_2_scheme,verify_token, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, Secret_Key, Algorithm,Token,get_password_hash,verify_password,get_current_user,get_current_admin,ADMIN_EMAIL,ADMIN_PASSWORD
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
import random
from nsepython import *
import yfinance as yf
from sqlalchemy import func,case
from Schema import schema 

models.Base.metadata.create_all(bind=engine)
def get_db(): 
    db = SessionLocal() 
    try: 
        yield db 
    finally: 
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


router = APIRouter()

@router.post("/contact", status_code=status.HTTP_201_CREATED)
async def create_user(contact:schema.ContactBase, db: db_dependency):
    cont = models.Contact(name = contact.name,email=contact.email,company=contact.company,phone=contact.phone,subject=contact.subject,message=contact.message)
    db.add(cont)
    db.commit() 
    return {"message": "successfully submitted contact form"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(user:schema.UserBase, db: db_dependency):
    query = db.query(models.User).filter(models.User.email == user.email).first()
    if query is None:
        hashed_password = get_password_hash(user.password)
        db_user = models.User(name=user.name, email=user.email, password=hashed_password, aadhar=user.aadhar, birth_date=user.birth_date)
        db.add(db_user)
        db.commit() 
        return {"message": "User registered successfully"}
    return {"message":"Email already exists"}

@router.post("/login", response_model=Token)
async def login( db:db_dependency,form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_EMAIL and form_data.password == ADMIN_PASSWORD:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
        data={"sub": form_data.username, "role" : "admin"},  
        expires_delta=access_token_expires
        )
        return {"access_token" : access_token, "token_type" : "bearer"}


    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email,"role":"user"}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/shares",status_code=status.HTTP_201_CREATED)
async def create_share(share: schema.ShareBase,db:db_dependency,admin:Annotated[dict,Depends(get_current_admin)]):
    if admin["role"]!='admin':
        raise HTTPException(status_code=401,detail="Unauthorized Access")
    db_product = models.Shares(sid=share.sid, name=share.name, price=share.price,description=share.description)
    db.add(db_product)
    db.commit()


@router.post("/order",status_code=status.HTTP_201_CREATED)
async def create_order(order: schema.OrderBase,db:db_dependency,current_user:Annotated[schema.UserBase,Depends(get_current_user)]):

    # here i am checking if user or share exist or not
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    # share = db.query(models.Shares).filter(models.Shares.sid == order.sid).first()

    if user is None:
        raise HTTPException(status_code=404,detail="User not found")
    order = models.Order(order_date=date.today(),sid=order.sid, uid=current_user.id,quantity = order.quantity,Otype = schema.OrderType.BUY,price=order.price)
    db.add(order)
    db.commit()

@router.post("/sell")
def sell_shares(request: schema.SellRequest, db: db_dependency,current_user:Annotated[schema.UserBase,Depends(get_current_user)]):
    # Calculate total BUY and SELL quantities
    total_bought = db.query(func.sum(models.Order.quantity)).filter(
        models.Order.uid == current_user.id,
        models.Order.sid == request.sid,
        models.Order.Otype == schema.OrderType.BUY
    ).scalar() or 0
 
    total_sold = db.query(func.sum(models.Order.quantity)).filter(
        models.Order.uid == current_user.id,
        models.Order.sid == request.sid,
        models.Order.Otype == schema.OrderType.SELL
    ).scalar() or 0
 
    current_holdings = total_bought - total_sold
 
    if current_holdings < request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient shares to sell.")

    try:
        symbol = yf.Ticker(request.sid)
        info = symbol.info
        price = info.get("regularMarketPrice",0)
    except Exception:
        raise HTTPException(status_code=500,detail="Failed to fetch stock price")

    total = price*request.quantity
    
 
    # Add a SELL order
    sell_order = models.Order(
        uid=current_user.id,
        sid=request.sid,
        quantity=request.quantity,
        Otype=schema.OrderType.SELL,
        order_date=date.today(),
        price=request.price
    )
    db.add(sell_order)

    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if user is None:
        raise HTTPException(status_code=404,detail="User not found")
    user.balance = user.balance + total

    db.commit()
 
    return {"message": "Shares sold successfully"}



#All Get methods
@router.get("/user/",status_code=status.HTTP_200_OK,response_model = schema.User2Base)
async def get_customer(db:db_dependency,current_user:Annotated[schema.UserBase,Depends(get_current_user)]):
    print(current_user)
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    return user

@router.get("/sharess",status_code=status.HTTP_200_OK)
async def get_shares():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    df = pd.DataFrame(positions['data'])
    dp = df[['symbol', 'identifier', 'series', 'open', 'dayHigh', 'dayLow', 'lastPrice', 'previousClose', 'change', 'pChange', 'totalTradedVolume', 'totalTradedValue', 'lastUpdateTime', 'yearHigh', 'yearLow', 'nearWKH', 'nearWKL', 'perChange365d', 'date365dAgo', 'chart365dPath', 'date30dAgo', 'perChange30d', 'chart30dPath', 'chartTodayPath', 'meta']]
    print(df.columns.tolist())
    return dp.astype(object).to_dict(orient="records")

@router.get("/shareDetails/{ticker}",status_code=status.HTTP_200_OK)
async def get_share_details(ticker:str):
    dat = yf.Ticker(ticker)
    data = dat.history(period='1y')
    data.reset_index(inplace=True)
    return data.astype(object).to_dict(orient="records")


@router.get("/shareInfo/{ticker}",status_code=status.HTTP_200_OK)
async def get_share_details(ticker:str):
    dat = yf.Ticker(ticker)
    data = dat.info
    print(data)
    return data

@router.get("/userOrders")
async def get_orders(db:db_dependency,current_user:Annotated[schema.Login,Depends(get_current_user)]):
    order = db.query(models.Order).filter(models.Order.uid == current_user.id).all()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No orders")
    return order

@router.get("/allOrders")
async def get_order_details(db:db_dependency,current_admin:Annotated[schema.Login,Depends(get_current_admin)]):
    order = db.query(models.Order).all()
    allOrders = []
    if order is None:
        return {"error": "Order not found"}
    for od in order:
        try:
            ticker_data = yf.Ticker(od.sid) 
            info = ticker_data.info
        except Exception as e:
            return {"error": f"Failed to fetch share data for {str(e)}"}
    
        allOrders.append( {
            "order_id": od.oid,
            "order_date": od.order_date,
            "quantity" : od.quantity,
            "type":od.Otype,
            "user": {
                "id": od.user.id,
                "name": od.user.name,
                "email": od.user.email,
                "aadhar": od.user.aadhar,
            },
            "shares": {
                "Symbol": od.sid,
                "name": info.get("shortName", "N/A"),
                "price": info.get("regularMarketPrice", "N/A"),
            },
            "total":od.quantity * info.get("regularMarketPrice", "N/A")
        })

    return allOrders

@router.get("/allUser/",status_code=status.HTTP_200_OK)
async def get_customer(db:db_dependency,current_user:Annotated[schema.Login,Depends(get_current_admin)]):
    user = db.query(models.User).all()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    return user

@router.get("/allContact/",status_code=status.HTTP_200_OK)
async def get_customer(db:db_dependency,current_user:Annotated[schema.Login,Depends(get_current_admin)]):
    contacts = db.query(models.Contact).all()
    if contacts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    return contacts

@router.get("/userShares", status_code=status.HTTP_200_OK)
async def get_user_shares(db: Annotated[Session, Depends(get_db)],current_user: Annotated[schema.UserBase, Depends(get_current_user)]):
    net_holdings = db.query(
        models.Order.sid.label("symbol"),
        func.sum(
            case(
                (models.Order.Otype == models.OrderType.BUY, models.Order.quantity),else_=-models.Order.quantity)
        ).label("net_quantity")
    ).filter(
        models.Order.uid == current_user.id
    ).group_by(
        models.Order.sid
    ).having(
        func.sum(
            case(
                (models.Order.Otype == models.OrderType.BUY, models.Order.quantity),
                else_=-models.Order.quantity
            )
        ) > 0  # Only include shares the user actually holds
    ).all()
 
    if not net_holdings:
        raise HTTPException(status_code=404, detail="User has no shares")
 
    shares_list = []
    for holding in net_holdings:
        try:
            ticker = yf.Ticker(holding.symbol)
            info = ticker.info
            price = info.get("regularMarketPrice", 0)
        except Exception:
            continue 
 
        shares_list.append({"symbol": holding.symbol,"name": info.get("shortName"),"price": price,"quantity": holding.net_quantity,"total": price * int(holding.net_quantity)})
 
    return shares_list
 
#All put methods
@router.put("/user",status_code=status.HTTP_204_NO_CONTENT)
async def update_customer(db:db_dependency,current_user:Annotated[schema.UserBase,Depends(get_current_user)]):
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
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
    return db_user

@router.put("/user/balance", status_code=status.HTTP_204_NO_CONTENT)
async def update_balance(balance_update: schema.BalanceUpdate,db: db_dependency,current_user: Annotated[schema.UserBase, Depends(get_current_user)]):
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
 
    db_user.balance = balance_update.balance
    db.add(db_user)
    db.commit()
 
    return {"message": "Balance updated successfully"}


# All delete methods
@router.delete("/user/{uid}")
async def delete_user(uid:int,db:db_dependency):
    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    db.delete(user)
    db.commit()


# All share methods of sql

# @router.put("/share/{sid}",status_code=status.HTTP_204_NO_CONTENT)
# async def update_product(sid: int,share:schema.ShareBase,db:db_dependency):
#     db_share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
#     if db_share is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
#     db_share.pid = share.sid
#     db_share.name = share.name
#     db_share.price = share.price
#     db_share.description = share.description
#     db.add(db_share)
#     db.commit()
#     return db_share


# @router.delete("/share/{sid}")
# async def delete_product(sid:int,db:db_dependency):
#     share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
#     if share is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
#     db.delete(share)
#     db.commit()

# @router.get("/share/{sid}",status_code=status.HTTP_200_OK)
# async def get_product(sid:int,db:db_dependency):
#     share = db.query(models.Shares).filter(models.Shares.sid == sid).first()
#     if share is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
#     return share


# @router.get("/shares",status_code=status.HTTP_200_OK)
# async def get_product(db:db_dependency):
#     shares = db.query(models.Shares).all()
#     if shares is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
#     return shares


# def update_price():
#     db:Session = SessionLocal()
#     shares=db.query(models.Shares).all()

#     for share in shares:
#         change_per = random.uniform(-0.02,0.02)
#         new_price = round(share.price*(1+change_per),2)

#         print(share.price)
#         share.prev_price = share.price
#         share.price = new_price
#         history=models.SharePrices(
#             share_id = share.sid,
#             price=new_price,
#             timeStamp=datetime.utcnow()
#         )
#         db.add(history)
#     db.commit()
#     db.close()