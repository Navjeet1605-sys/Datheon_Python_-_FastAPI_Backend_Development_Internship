# Task 2 - User authentication and role based access (RBAC) with JWT


import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

# ---------------- settings ----------------
# in real life keep the secret in an environment variable, never in the code
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-before-using")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(title="Auth API", description="JWT login with user and admin roles")

# ---------------- fake database ----------------
# username -> {username, hashed_password, role}
users_db = {}


@app.on_event("startup")
def create_admin():
    # one admin account so we can test the admin-only route
    users_db["admin"] = {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
    }


# ---------------- models ----------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str


# ---------------- helper functions ----------------
def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    data = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    error = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise error
    except JWTError:
        raise error

    user = users_db.get(username)
    if user is None:
        raise error
    return user


def require_role(role: str):
    """Returns a dependency that only lets users with the given role in."""

    async def check(user: dict = Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="You do not have permission")
        return user

    return check


# ---------------- endpoints ----------------
@app.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserCreate):
    if data.username in users_db:
        raise HTTPException(status_code=400, detail="Username already taken")

    # everyone who registers is a normal user, admins can't be self-created
    users_db[data.username] = {
        "username": data.username,
        "hashed_password": pwd_context.hash(data.password),
        "role": "user",
    }
    return users_db[data.username]


@app.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form.username)

    if user is None or not pwd_context.verify(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Wrong username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user["username"], user["role"])
    return {"access_token": token, "token_type": "bearer"}


# any logged in user
@app.get("/me", response_model=UserOut)
async def read_me(current_user: dict = Depends(get_current_user)):
    return current_user


# any logged in user
@app.get("/protected")
async def protected_data(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, this data is only for logged in users"}


# admin only
@app.get("/admin/users", response_model=list[UserOut])
async def list_users(admin: dict = Depends(require_role("admin"))):
    return list(users_db.values())
