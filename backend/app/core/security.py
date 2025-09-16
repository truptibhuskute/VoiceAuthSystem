"""
Security utilities for voice authentication system

Handles:
1. Voiceprint encryption/decryption
2. Token generation and validation
3. Password hashing
4. Rate limiting
5. Input validation
"""

import secrets
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt
from passlib.context import CryptContext
import base64
import os

from app.core.config import settings


class VoiceprintEncryption:
    """
    Secure encryption/decryption for voiceprint data
    """
    
    def __init__(self):
        self.iterations = 100000  # PBKDF2 iterations
        
    def generate_salt(self) -> str:
        """Generate a random salt for encryption"""
        return secrets.token_hex(16)
    
    def _derive_key(self, password: str, salt: str) -> bytes:
        """Derive encryption key from password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=self.iterations,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_voiceprint(self, voiceprint: Dict[str, Any], user_id: str, salt: str) -> bytes:
        """
        Encrypt voiceprint data using user-specific key
        
        Args:
            voiceprint: Voiceprint dictionary
            user_id: User identifier
            salt: Random salt for encryption
            
        Returns:
            Encrypted voiceprint bytes
        """
        # Create user-specific encryption key
        key_material = f"{settings.SECRET_KEY}_{user_id}"
        key = self._derive_key(key_material, salt)
        
        # Initialize Fernet cipher
        cipher = Fernet(key)
        
        # Serialize voiceprint (convert numpy arrays to lists)
        serializable_voiceprint = self._make_serializable(voiceprint)
        voiceprint_bytes = pickle.dumps(serializable_voiceprint)
        
        # Encrypt
        encrypted_data = cipher.encrypt(voiceprint_bytes)
        
        return encrypted_data
    
    def decrypt_voiceprint(self, encrypted_data: bytes, user_id: str, salt: str) -> Dict[str, Any]:
        """
        Decrypt voiceprint data
        
        Args:
            encrypted_data: Encrypted voiceprint bytes
            user_id: User identifier
            salt: Salt used for encryption
            
        Returns:
            Decrypted voiceprint dictionary
        """
        # Recreate the same key
        key_material = f"{settings.SECRET_KEY}_{user_id}"
        key = self._derive_key(key_material, salt)
        
        # Initialize Fernet cipher
        cipher = Fernet(key)
        
        try:
            # Decrypt and deserialize
            decrypted_bytes = cipher.decrypt(encrypted_data)
            voiceprint = pickle.loads(decrypted_bytes)
            
            return self._restore_numpy_arrays(voiceprint)
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt voiceprint: {str(e)}")
    
    def _make_serializable(self, data: Any) -> Any:
        """Convert numpy arrays to lists for JSON serialization"""
        import numpy as np
        
        if isinstance(data, dict):
            return {k: self._make_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_serializable(item) for item in data]
        elif isinstance(data, np.ndarray):
            return {'__numpy_array__': data.tolist(), '__dtype__': str(data.dtype)}
        elif isinstance(data, (np.integer, np.floating)):
            return data.item()
        else:
            return data
    
    def _restore_numpy_arrays(self, data: Any) -> Any:
        """Restore numpy arrays from serialized format"""
        import numpy as np
        
        if isinstance(data, dict):
            if '__numpy_array__' in data and '__dtype__' in data:
                return np.array(data['__numpy_array__'], dtype=data['__dtype__'])
            else:
                return {k: self._restore_numpy_arrays(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._restore_numpy_arrays(item) for item in data]
        else:
            return data


class AuthTokens:
    """
    JWT token management for authentication
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def create_access_token(self, data: Dict[str, Any], 
                           expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)


class SecurityValidator:
    """
    Input validation and security checks
    """
    
    @staticmethod
    def validate_audio_file(file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate uploaded audio file
        
        Args:
            file_data: Audio file bytes
            filename: Original filename
            
        Returns:
            Validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check file size
        if len(file_data) > settings.MAX_FILE_SIZE:
            result["valid"] = False
            result["errors"].append(f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE} bytes")
        
        # Check file extension
        if filename:
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            if extension not in settings.ALLOWED_AUDIO_FORMATS:
                result["valid"] = False
                result["errors"].append(f"File format '{extension}' not supported. Allowed formats: {settings.ALLOWED_AUDIO_FORMATS}")
        
        # Check for minimum file size (avoid empty files)
        if len(file_data) < 1000:  # Less than 1KB
            result["valid"] = False
            result["errors"].append("Audio file appears to be too small or corrupted")
        
        # Basic audio format validation (check for common audio headers)
        audio_signatures = {
            b'RIFF': 'wav',
            b'ID3': 'mp3',
            b'\xff\xfb': 'mp3',
            b'\xff\xf3': 'mp3',
            b'\xff\xf2': 'mp3',
            b'OggS': 'ogg'
        }
        
        has_valid_signature = False
        for signature in audio_signatures:
            if file_data.startswith(signature):
                has_valid_signature = True
                break
        
        if not has_valid_signature:
            result["warnings"].append("Audio file format could not be verified")
        
        return result
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """Validate username format and security"""
        result = {"valid": True, "errors": []}
        
        if not username or len(username.strip()) == 0:
            result["valid"] = False
            result["errors"].append("Username cannot be empty")
            return result
        
        username = username.strip()
        
        # Length check
        if len(username) < 3 or len(username) > 50:
            result["valid"] = False
            result["errors"].append("Username must be between 3 and 50 characters")
        
        # Character validation
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            result["valid"] = False
            result["errors"].append("Username can only contain letters, numbers, dots, hyphens, and underscores")
        
        # Prohibited patterns
        prohibited = ['admin', 'root', 'test', 'user', 'guest']
        if username.lower() in prohibited:
            result["valid"] = False
            result["errors"].append("Username not allowed")
        
        return result
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """Validate email format"""
        result = {"valid": True, "errors": []}
        
        if not email or len(email.strip()) == 0:
            result["valid"] = False
            result["errors"].append("Email cannot be empty")
            return result
        
        email = email.strip().lower()
        
        # Basic email regex
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result["valid"] = False
            result["errors"].append("Invalid email format")
        
        # Length check
        if len(email) > 100:
            result["valid"] = False
            result["errors"].append("Email address too long")
        
        return result


class RateLimiter:
    """
    Simple in-memory rate limiter for authentication attempts
    """
    
    def __init__(self):
        self.attempts = {}  # {key: [(timestamp, count), ...]}
        self.max_attempts = 5
        self.window_seconds = 300  # 5 minutes
        self.lockout_seconds = 900  # 15 minutes
    
    def is_rate_limited(self, key: str) -> Dict[str, Any]:
        """
        Check if key (IP/user) is rate limited
        
        Args:
            key: Identifier to check (IP address, user ID, etc.)
            
        Returns:
            Rate limit status
        """
        now = datetime.utcnow().timestamp()
        
        # Clean old attempts
        if key in self.attempts:
            self.attempts[key] = [
                (timestamp, count) for timestamp, count in self.attempts[key]
                if now - timestamp < self.window_seconds
            ]
        
        if key not in self.attempts:
            return {"limited": False, "remaining": self.max_attempts}
        
        # Count recent attempts
        recent_attempts = sum(count for _, count in self.attempts[key])
        
        # Check if locked out
        if recent_attempts >= self.max_attempts:
            # Find the earliest attempt that counts towards lockout
            earliest_lockout_attempt = min(
                timestamp for timestamp, _ in self.attempts[key]
                if now - timestamp < self.lockout_seconds
            )
            
            time_until_unlock = self.lockout_seconds - (now - earliest_lockout_attempt)
            
            if time_until_unlock > 0:
                return {
                    "limited": True,
                    "remaining": 0,
                    "unlock_at": datetime.utcnow() + timedelta(seconds=time_until_unlock)
                }
        
        return {
            "limited": False,
            "remaining": max(0, self.max_attempts - recent_attempts)
        }
    
    def record_attempt(self, key: str, success: bool = False):
        """
        Record an authentication attempt
        
        Args:
            key: Identifier (IP address, user ID, etc.)
            success: Whether the attempt was successful
        """
        now = datetime.utcnow().timestamp()
        
        if key not in self.attempts:
            self.attempts[key] = []
        
        # If successful, clear the attempts
        if success:
            self.attempts[key] = []
        else:
            # Record failed attempt
            self.attempts[key].append((now, 1))


# Global instances
voiceprint_encryption = VoiceprintEncryption()
auth_tokens = AuthTokens()
security_validator = SecurityValidator()
rate_limiter = RateLimiter()
