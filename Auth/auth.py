from fastapi import Depends,HTTPException , status
from datetime import date, datetime, timedelta 
from jose import JWTError, jwt 
from passlib.context import CryptContext 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from pydantic import BaseModel
from typing import Annotated, Optional
from sqlalchemy.orm import Session 
from Database.database import engine, SessionLocal 
from Models import models


def get_db(): 
    db = SessionLocal() 
    try: 
        yield db 
    finally: 
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


Secret_Key = "3237baaabf280097a71b50cff1e521c7b1cae53ae114b4f4772d998a0c5d9c6e"
Algorithm = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'admin1'


class Token(BaseModel): 
    access_token: str 
    token_type: str

class TokenData(BaseModel): 
    username: Optional[str] = None


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto") 
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def verify_password(plain_password :str, hashed_password:str)->bool: 
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password:str)->str: 
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None): 
    to_encode = data.copy() 
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15)) 
    to_encode.update({"exp": expire}) 
    encoded_jwt = jwt.encode(to_encode, Secret_Key, algorithm=Algorithm) 
    return encoded_jwt


def verify_token(token:str=Depends(oauth_2_scheme)):
    try:
        payload = jwt.decode(token,Secret_Key,algorithm=[Algorithm])
        email:str = payload.get("sub")
        role:str = payload.get("role")
        if email is None:
            raise HTTPException(status_code=status_HTTP_401_UNAUTHORIZED,detail="Invalid Token",headers={"WWW-Authenticate":"Bearer"})
            return {"email":email,"role":role}
    except JWTError:
        raise HTTPException(status_code=status_HTTP_401_UNAUTHORIZED,detail="Invalid token or expired",headers={"WWW-Authenticate":"Bearer"})


def get_current_user(token: str = Depends(oauth_2_scheme), db: Session=Depends(get_db)): 
    credentials_exception = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") 
    try: 
        payload = jwt.decode(token, Secret_Key, algorithms=[Algorithm]) 
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None: 
            raise credentials_exception 
    except JWTError: 
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(token: str = Depends(oauth_2_scheme), db: Session=Depends(get_db)): 
    credentials_exception = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", ) 
    try: 
        payload = jwt.decode(token, Secret_Key, algorithms=[Algorithm]) 
        role: str = payload.get("role") 
        if role != 'admin': 
            raise credentials_exception 
    except JWTError: 
        raise credentials_exception
    return {'email':payload.get('sub'),"role":role}
