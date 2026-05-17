"""Modelos ORM — evolução gradual do Indupack."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Apontamento(Base):
    """Histórico de apontamento de produção (total absoluto lançado na máquina)."""

    __tablename__ = "apontamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    maquina: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operador: Mapped[str] = mapped_column(String(200), default="")
    produto: Mapped[str] = mapped_column(String(500), default="")
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(80), default="")
    horario: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    turno: Mapped[str] = mapped_column(String(80), default="")


class SystemSettings(Base):
    """Parâmetros globais (uma linha id=1), JSON versionado no campo config_json."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class OperatorProfile(Base):
    """Operadores / perfis de chão (cadastro administrativo — não substitui usuários de login)."""

    __tablename__ = "operator_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    turno_padrao: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    nivel_acesso: Mapped[str] = mapped_column(String(80), nullable=False, default="operador")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TabletSessao(Base):
    """Sessão persistente do terminal tablet (sobrevive a restart/deploy do servidor)."""

    __tablename__ = "tablet_sessoes"

    maquina_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tablet_vinculado: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    manutencao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manutencao_msg: Mapped[str] = mapped_column(String(200), nullable=False, default="TERMINAL EM MANUTENÇÃO")
    kiosk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ultimo_acesso_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultimo_ip: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    bateria_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bateria_carregando: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sessao_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reiniciar_em: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reiniciar_ok_em: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class StopMotive(Base):
    """Catálogo administrativo de motivos de parada (para padronizar apontamentos)."""

    __tablename__ = "stop_motives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    rotulo: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    categoria: Mapped[str] = mapped_column(String(80), nullable=False, default="geral")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
