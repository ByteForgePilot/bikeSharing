from app.repositories import user as user_repo
from app.core.security import pwd_context


async def register_user(db, username: str, password: str):
    existing = await user_repo.get_by_username(db, username)
    if existing:
        raise ValueError("Username already exists")
    return await user_repo.create(
        db, username=username, password_hash=pwd_context.hash(password)
    )


async def authenticate_user(db, username: str, password: str):
    user = await user_repo.get_by_username(db, username)
    if not user or not pwd_context.verify(password, user.password_hash):
        raise ValueError("Invalid credentials")
    return user
