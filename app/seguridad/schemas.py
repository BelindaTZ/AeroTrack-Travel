from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: str
    email: str
    nombre_completo: str
    tipo_actor: str
    rol_id: str | None = None
    activo: bool
