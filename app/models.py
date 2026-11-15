from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./gingasegura.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, keywords={}) if False else create_engine(SQLALCHEMY_DATABASE_URL,connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class Turma(Base):
    __tablename__ = "turmas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    horario: Mapped[srr] = mapped_column(String(50), nullable=False)

class Aluno(Base):
    __tablename__ = "alunos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    apelido: Mapped[str] = mapped_column(String(60), nullable=False)
    corda: Mapped[srr] = mapped_column(String(50), nullable=False)
    alergia: Mapped[srr] = mapped_column(String(150), default="Nenhuma")
    restricao_medica: Mapped[str] = mapped_column(String(150), default="Nenhuma")
    responsavel_nome: Mapped[str] = mapped_column(String(120), nullable=False)
    responsavel_telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"), nullable=False)

class Frequencia(Base):
    __tablename__ = "frequencias"
    __table_args__ = (UniqueConstraint("aluno_id", "data_aula", name="uq_aluno_data"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    data_aula: Mapped[date] = mapped_column(Date, nullable=False)
    presente: Mapped[bool] = mapped_column(Boolean, default=True)
