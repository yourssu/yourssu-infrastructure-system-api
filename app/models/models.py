from sqlalchemy import Column, Integer, String, BigInteger, Text, TIMESTAMP, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from core.database import Base
from core.enums import UserRole, UserPart, DeploymentState

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(128), unique=True, nullable=False)
    nickname = Column(String(64), nullable=False)
    part = Column(Enum(UserPart), nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    accesses = Column(JSON, nullable=False, default=list) # TODO: 추후 삭제
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    deleted_at = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True) # TODO: 추후 False로 변경
    avatar_id = Column(Integer, nullable=False, default=1)
    
    applications = relationship("Application", back_populates="user")
    deployments = relationship("Deployment", foreign_keys="Deployment.user_id", back_populates="user")
    admin_deployments = relationship("Deployment", foreign_keys="Deployment.admin_id", back_populates="admin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan") 

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    deleted_at = Column(TIMESTAMP, nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    user = relationship("User", back_populates="applications")
    deployments = relationship("Deployment", back_populates="application")

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    domain_name = Column(String(32), nullable=False)
    cpu_requests = Column(String(16), nullable=False)
    memory_requests = Column(String(16), nullable=False)
    cpu_limits = Column(String(16), nullable=False)
    memory_limits = Column(String(16), nullable=False)
    port = Column(Integer, nullable=False)
    image_url = Column(String(2048), nullable=True)
    replicas = Column(Integer, nullable=False, default=1)
    message = Column(Text, nullable=True, default=None)
    comment = Column(Text, nullable=True, default=None)
    state = Column(Enum(DeploymentState), nullable=False, default=DeploymentState.REQUEST)
    is_applied = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    deleted_at = Column(TIMESTAMP, nullable=True)
    application_id = Column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    admin_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    application = relationship("Application", back_populates="deployments")
    user = relationship("User", foreign_keys=[user_id], back_populates="deployments")
    admin = relationship("User", foreign_keys=[admin_id], back_populates="admin_deployments")
    manifests = relationship("Manifest", back_populates="deployment", primaryjoin="and_(Deployment.id==Manifest.deployment_id, Manifest.deleted_at==None)")

class Manifest(Base):
    __tablename__ = "manifests"
    
    id = Column(BigInteger, primary_key=True, index=True)
    file_name = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    deleted_at = Column(TIMESTAMP, nullable=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False)
    
    deployment = relationship("Deployment", back_populates="manifests")

class Template(Base):
    __tablename__ = "templates"
    
    id = Column(BigInteger, primary_key=True, index=True)
    file_name = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.now)
    deleted_at = Column(TIMESTAMP, nullable=True)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BigInteger, primary_key=True, index=True)
    token = Column(String(512), unique=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.now)

    user = relationship("User", back_populates="refresh_tokens") 