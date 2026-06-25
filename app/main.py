from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship


# =========================
# CONFIGURAÇÕES GERAIS
# =========================

DATABASE_URL = "sqlite:///./raizes.db"
SECRET_KEY = "chave-secreta-projeto-raizes"
ALGORITHM = "HS256"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


app = FastAPI(
    title="API Raízes do Nordeste",
    version="1.0.0",
    description="API Back-End para gerenciamento de pedidos, produtos, pagamentos mock e rastreabilidade por canalPedido."
)


# =========================
# ENUMS
# =========================

class PerfilUsuario(str, Enum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


class CanalPedido(str, Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(str, Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


# =========================
# MODELS SQLALCHEMY
# =========================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    perfil = Column(String, nullable=False, default=PerfilUsuario.CLIENTE.value)
    criado_em = Column(DateTime, default=datetime.utcnow)

    pedidos = relationship("Pedido", back_populates="cliente")


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    preco = Column(Float, nullable=False)
    estoque = Column(Integer, nullable=False, default=0)
    ativo = Column(Integer, nullable=False, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(Integer, nullable=False)
    canal_pedido = Column(String, nullable=False)
    status = Column(String, nullable=False, default=StatusPedido.AGUARDANDO_PAGAMENTO.value)
    valor_total = Column(Float, nullable=False, default=0)
    criado_em = Column(DateTime, default=datetime.utcnow)

    cliente = relationship("Usuario", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido")
    pagamento = relationship("Pagamento", back_populates="pedido", uselist=False)


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    status_pagamento = Column(String, nullable=False)
    mensagem = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    pedido = relationship("Pedido", back_populates="pagamento")


Base.metadata.create_all(bind=engine)


# =========================
# SCHEMAS PYDANTIC
# =========================

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: PerfilUsuario = PerfilUsuario.CLIENTE


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProdutoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    estoque: int


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    preco: float
    estoque: int
    ativo: int

    model_config = ConfigDict(from_attributes=True)


class ItemPedidoCreate(BaseModel):
    produto_id: int = Field(alias="produtoId")
    quantidade: int

    model_config = ConfigDict(populate_by_name=True)


class PedidoCreate(BaseModel):
    canal_pedido: CanalPedido = Field(alias="canalPedido")
    cliente_id: int = Field(alias="clienteId")
    unidade_id: int = Field(alias="unidadeId")
    itens: List[ItemPedidoCreate]
    forma_pagamento: str = Field(alias="formaPagamento")

    model_config = ConfigDict(populate_by_name=True)


class AtualizarStatusRequest(BaseModel):
    status: StatusPedido


class PagamentoMockRequest(BaseModel):
    pedido_id: int = Field(alias="pedidoId")
    aprovado: bool

    model_config = ConfigDict(populate_by_name=True)


# =========================
# FUNÇÕES AUXILIARES
# =========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def gerar_hash_senha(senha: str) -> str:
    return sha256(senha.encode("utf-8")).hexdigest()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return gerar_hash_senha(senha) == senha_hash


def criar_token(usuario: Usuario) -> str:
    payload = {
        "sub": usuario.email,
        "perfil": usuario.perfil,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return usuario


def exigir_perfil(usuario: Usuario, perfis_permitidos: list[str]):
    if usuario.perfil not in perfis_permitidos:
        raise HTTPException(
            status_code=403,
            detail={
                "erro": "ACESSO_NEGADO",
                "mensagem": "Usuário não possui permissão para executar esta ação."
            }
        )


def formatar_pedido(pedido: Pedido):
    return {
        "id": pedido.id,
        "clienteId": pedido.cliente_id,
        "unidadeId": pedido.unidade_id,
        "canalPedido": pedido.canal_pedido,
        "status": pedido.status,
        "valorTotal": pedido.valor_total,
        "itens": [
            {
                "produtoId": item.produto_id,
                "quantidade": item.quantidade,
                "precoUnitario": item.preco_unitario
            }
            for item in pedido.itens
        ],
        "pagamento": {
            "status": pedido.pagamento.status_pagamento,
            "mensagem": pedido.pagamento.mensagem
        } if pedido.pagamento else None
    }


# =========================
# ROTAS
# =========================

@app.get("/")
def home():
    return {
        "mensagem": "API Raízes do Nordeste funcionando com sucesso!",
        "documentacao": "/docs"
    }


@app.post("/usuarios", response_model=UsuarioResponse, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if usuario_existente:
        raise HTTPException(
            status_code=409,
            detail={
                "erro": "EMAIL_JA_CADASTRADO",
                "mensagem": "Já existe um usuário cadastrado com este e-mail."
            }
        )

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil=dados.perfil.value
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return novo_usuario


@app.post("/auth/login", response_model=TokenResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail={
                "erro": "CREDENCIAIS_INVALIDAS",
                "mensagem": "E-mail ou senha inválidos."
            }
        )

    token = criar_token(usuario)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/produtos", response_model=ProdutoResponse, status_code=201)
def criar_produto(
    dados: ProdutoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    exigir_perfil(usuario, [PerfilUsuario.ADMIN.value, PerfilUsuario.GERENTE.value])

    if dados.preco <= 0:
        raise HTTPException(status_code=422, detail="O preço do produto deve ser maior que zero.")

    if dados.estoque < 0:
        raise HTTPException(status_code=422, detail="O estoque não pode ser negativo.")

    produto = Produto(
        nome=dados.nome,
        descricao=dados.descricao,
        preco=dados.preco,
        estoque=dados.estoque,
        ativo=1
    )

    db.add(produto)
    db.commit()
    db.refresh(produto)

    return produto


@app.get("/produtos", response_model=list[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(Produto).filter(Produto.ativo == 1).all()


@app.get("/estoque/{produto_id}")
def consultar_estoque(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    return {
        "produtoId": produto.id,
        "nome": produto.nome,
        "estoque": produto.estoque
    }


@app.post("/pedidos", status_code=201)
def criar_pedido(
    dados: PedidoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    if not dados.itens:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "PEDIDO_SEM_ITENS",
                "mensagem": "O pedido deve possuir ao menos um item."
            }
        )

    cliente = db.query(Usuario).filter(Usuario.id == dados.cliente_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    valor_total = 0
    itens_calculados = []

    for item in dados.itens:
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail={
                    "erro": "PRODUTO_NAO_ENCONTRADO",
                    "mensagem": f"Produto {item.produto_id} não encontrado."
                }
            )

        if produto.ativo != 1:
            raise HTTPException(status_code=409, detail="Produto inativo.")

        if item.quantidade <= 0:
            raise HTTPException(status_code=422, detail="A quantidade deve ser maior que zero.")

        if produto.estoque < item.quantidade:
            raise HTTPException(
                status_code=409,
                detail={
                    "erro": "ESTOQUE_INSUFICIENTE",
                    "mensagem": f"Estoque insuficiente para o produto {produto.nome}."
                }
            )

        valor_total += produto.preco * item.quantidade
        itens_calculados.append((produto, item.quantidade))

    pedido = Pedido(
        cliente_id=dados.cliente_id,
        unidade_id=dados.unidade_id,
        canal_pedido=dados.canal_pedido.value,
        status=StatusPedido.AGUARDANDO_PAGAMENTO.value,
        valor_total=valor_total
    )

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    for produto, quantidade in itens_calculados:
        produto.estoque -= quantidade

        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=quantidade,
            preco_unitario=produto.preco
        )

        db.add(item_pedido)

    db.commit()
    db.refresh(pedido)

    return formatar_pedido(pedido)


@app.get("/pedidos")
def listar_pedidos(
    canalPedido: Optional[CanalPedido] = None,
    status: Optional[StatusPedido] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    consulta = db.query(Pedido)

    if canalPedido:
        consulta = consulta.filter(Pedido.canal_pedido == canalPedido.value)

    if status:
        consulta = consulta.filter(Pedido.status == status.value)

    pedidos = consulta.all()

    return [formatar_pedido(pedido) for pedido in pedidos]


@app.get("/pedidos/{pedido_id}")
def consultar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    return formatar_pedido(pedido)


@app.put("/pedidos/{pedido_id}/status")
def atualizar_status_pedido(
    pedido_id: int,
    dados: AtualizarStatusRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    exigir_perfil(usuario, [
        PerfilUsuario.ATENDENTE.value,
        PerfilUsuario.GERENTE.value,
        PerfilUsuario.ADMIN.value
    ])

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    pedido.status = dados.status.value
    db.commit()
    db.refresh(pedido)

    return formatar_pedido(pedido)


@app.post("/pagamentos/mock")
def pagamento_mock(
    dados: PagamentoMockRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    pedido = db.query(Pedido).filter(Pedido.id == dados.pedido_id).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status not in [
        StatusPedido.AGUARDANDO_PAGAMENTO.value,
        StatusPedido.PAGAMENTO_RECUSADO.value
    ]:
        raise HTTPException(
            status_code=409,
            detail={
                "erro": "PAGAMENTO_NAO_PERMITIDO",
                "mensagem": "O pedido não está em uma etapa válida para pagamento."
            }
        )

    if dados.aprovado:
        status_pagamento = "APROVADO"
        mensagem = "Pagamento mock aprovado com sucesso."
        pedido.status = StatusPedido.PAGO.value
    else:
        status_pagamento = "RECUSADO"
        mensagem = "Pagamento mock recusado."
        pedido.status = StatusPedido.PAGAMENTO_RECUSADO.value

    pagamento = Pagamento(
        pedido_id=pedido.id,
        status_pagamento=status_pagamento,
        mensagem=mensagem
    )

    db.add(pagamento)
    db.commit()
    db.refresh(pedido)

    return {
        "pedidoId": pedido.id,
        "statusPedido": pedido.status,
        "statusPagamento": status_pagamento,
        "mensagem": mensagem
    }


@app.get("/fidelidade/{cliente_id}")
def consultar_fidelidade(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual)
):
    cliente = db.query(Usuario).filter(Usuario.id == cliente_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    pedidos_pagos = db.query(Pedido).filter(
        Pedido.cliente_id == cliente_id,
        Pedido.status.in_([
            StatusPedido.PAGO.value,
            StatusPedido.ENTREGUE.value
        ])
    ).all()

    total_gasto = sum(p.valor_total for p in pedidos_pagos)
    pontos = int(total_gasto // 10)

    return {
        "clienteId": cliente_id,
        "nome": cliente.nome,
        "pontos": pontos,
        "regra": "1 ponto a cada R$ 10,00 em pedidos pagos ou entregues."
    }