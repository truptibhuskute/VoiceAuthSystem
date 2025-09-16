"""
Database models for user management and voice authentication
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Boolean, Text, LargeBinary, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Import Base from database module
from app.core.database import Base


class User(Base):
    """User model for authentication system"""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Use String for SQLite compatibility
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_enrolled = Column(Boolean, default=False)  # Voice enrollment status
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Voice authentication attempts
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    voiceprint = relationship("VoicePrint", back_populates="user", uselist=False)
    auth_logs = relationship("AuthenticationLog", back_populates="user")
    security_events = relationship("SecurityEvent", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class VoicePrint(Base):
    """Encrypted voiceprint storage for each user"""
    
    __tablename__ = "voiceprints"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, unique=True)  # One voiceprint per user
    
    # Relationship
    user = relationship("User", back_populates="voiceprint")
    
    # Encrypted voice features (never store raw audio!)
    encrypted_features = Column(LargeBinary, nullable=False)  # Encrypted MFCC/spectral features
    feature_hash = Column(String(64), nullable=False)  # Hash for integrity check
    
    # Metadata
    enrollment_quality = Column(Float, nullable=False)  # Quality score during enrollment
    feature_version = Column(String(10), default="1.0")  # For future model upgrades
    
    # Enrollment details
    enrollment_duration = Column(Float, nullable=False)  # Audio duration used
    enrollment_device_info = Column(Text, nullable=True)  # Device/browser info
    
    # Security
    salt = Column(String(32), nullable=False)  # For encryption
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<VoicePrint(id={self.id}, user_id={self.user_id})>"


class AuthenticationLog(Base):
    """Log all authentication attempts for security monitoring"""
    
    __tablename__ = "auth_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)  # Null for failed attempts
    
    # Relationship
    user = relationship("User", back_populates="auth_logs")
    
    # Authentication details
    auth_type = Column(String(20), nullable=False)  # 'enrollment', 'verification'
    success = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=True)  # Similarity/confidence score
    liveness_score = Column(Float, nullable=True)  # Anti-spoofing score
    
    # Request details
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(64), nullable=True)
    
    # Error details (if failed)
    error_code = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Processing time
    processing_time_ms = Column(Integer, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AuthLog(id={self.id}, user_id={self.user_id}, success={self.success})>"


class SecurityEvent(Base):
    """Track security events and potential threats"""
    
    __tablename__ = "security_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="security_events")
    
    # Event details
    event_type = Column(String(30), nullable=False)  # 'brute_force', 'spoofing_attempt', etc.
    severity = Column(String(10), nullable=False)  # 'low', 'medium', 'high', 'critical'
    description = Column(Text, nullable=False)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON string for extra context
    
    # Response
    action_taken = Column(String(50), nullable=True)  # 'account_locked', 'ip_blocked', etc.
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"
