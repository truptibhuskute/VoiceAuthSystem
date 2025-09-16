"""
Voice Authentication API Endpoints

Provides REST API for:
1. User enrollment with voice biometrics
2. Voice-based authentication
3. User management
4. System status and health checks
"""

import io
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

import librosa
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    voiceprint_encryption, auth_tokens, security_validator, rate_limiter
)
from app.models.user import User, VoicePrint, AuthenticationLog, SecurityEvent
from ml_engine.voice_processor import VoiceProcessor

# Initialize router and dependencies
router = APIRouter()
security = HTTPBearer()
voice_processor = VoiceProcessor(sample_rate=settings.SAMPLE_RATE)

# Pydantic models for request/response
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)

class EnrollmentResult(BaseModel):
    success: bool
    message: str
    quality_score: Optional[float] = None
    enrollment_id: Optional[str] = None
    warnings: Optional[list] = None

class VerificationRequest(BaseModel):
    username: str

class VerificationResult(BaseModel):
    success: bool
    message: str
    confidence_score: Optional[float] = None
    liveness_score: Optional[float] = None
    user_id: Optional[str] = None
    access_token: Optional[str] = None

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_enrolled: bool
    created_at: datetime
    last_login: Optional[datetime]

class SystemStatus(BaseModel):
    status: str
    version: str
    voice_engine: str
    security_features: list


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                    db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token"""
    token_data = auth_tokens.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=Dict[str, Any])
async def register_user(user_data: UserRegistration, 
                       request: Request,
                       db: Session = Depends(get_db)):
    """
    Register a new user (without voice enrollment)
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    try:
        # Validate input data
        username_validation = security_validator.validate_username(user_data.username)
        if not username_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": username_validation["errors"]}
            )
        
        email_validation = security_validator.validate_email(user_data.email)
        if not email_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": email_validation["errors"]}
            )
        
        # Check for existing users
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already registered"
            )
        
        # Create new user
        new_user = User(
            username=user_data.username,
            email=user_data.email.lower(),
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
            is_enrolled=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Log the registration
        log_entry = AuthenticationLog(
            user_id=new_user.id,
            auth_type="registration",
            success=True,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "success": True,
            "message": "User registered successfully. Please proceed with voice enrollment.",
            "user_id": str(new_user.id),
            "next_step": "voice_enrollment"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log security event
        security_event = SecurityEvent(
            event_type="registration_error",
            severity="medium",
            description=f"Registration failed: {str(e)}",
            ip_address=client_ip
        )
        db.add(security_event)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to internal error"
        )


@router.post("/enroll", response_model=EnrollmentResult)
async def enroll_voice(username: str,
                      request: Request,
                      audio_file: UploadFile = File(...),
                      db: Session = Depends(get_db)):
    """
    Enroll user's voice for biometric authentication
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Rate limiting
    rate_limit_key = f"enroll_{client_ip}"
    rate_status = rate_limiter.is_rate_limited(rate_limit_key)
    if rate_status["limited"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many enrollment attempts. Try again later."
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_enrolled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already enrolled. Use re-enrollment endpoint to update."
            )
        
        # Read and validate audio file
        audio_data = await audio_file.read()
        validation_result = security_validator.validate_audio_file(audio_data, audio_file.filename)
        
        if not validation_result["valid"]:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": validation_result["errors"]}
            )
        
        # Load audio using librosa
        try:
            audio_array, sr = librosa.load(io.BytesIO(audio_data), sr=settings.SAMPLE_RATE)
        except Exception as e:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process audio file: {str(e)}"
            )
        
        # Check audio duration
        duration = len(audio_array) / sr
        if duration < settings.MIN_AUDIO_DURATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio too short. Minimum {settings.MIN_AUDIO_DURATION} seconds required."
            )
        
        if duration > settings.MAX_AUDIO_DURATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio too long. Maximum {settings.MAX_AUDIO_DURATION} seconds allowed."
            )
        
        # Create voiceprint
        voiceprint, quality_score = voice_processor.create_voiceprint(audio_array)
        
        # Check quality score
        if quality_score < 0.5:  # Minimum quality threshold
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Voice quality too low (score: {quality_score:.2f}). Please try again with clearer audio."
            )
        
        # Encrypt and store voiceprint
        salt = voiceprint_encryption.generate_salt()
        encrypted_features = voiceprint_encryption.encrypt_voiceprint(
            voiceprint, str(user.id), salt
        )
        feature_hash = voice_processor.generate_feature_hash(voiceprint)
        
        # Save to database
        voice_print = VoicePrint(
            user_id=user.id,
            encrypted_features=encrypted_features,
            feature_hash=feature_hash,
            enrollment_quality=quality_score,
            enrollment_duration=duration,
            enrollment_device_info=request.headers.get("User-Agent"),
            salt=salt
        )
        
        db.add(voice_print)
        
        # Update user enrollment status
        user.is_enrolled = True
        user.is_verified = True
        
        db.commit()
        db.refresh(voice_print)
        
        # Log successful enrollment
        log_entry = AuthenticationLog(
            user_id=user.id,
            auth_type="enrollment",
            success=True,
            confidence_score=quality_score,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        db.add(log_entry)
        db.commit()
        
        rate_limiter.record_attempt(rate_limit_key, success=True)
        
        return EnrollmentResult(
            success=True,
            message="Voice enrollment successful!",
            quality_score=quality_score,
            enrollment_id=str(voice_print.id),
            warnings=validation_result.get("warnings", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log security event
        security_event = SecurityEvent(
            user_id=user.id if 'user' in locals() else None,
            event_type="enrollment_error",
            severity="high",
            description=f"Enrollment failed: {str(e)}",
            ip_address=client_ip
        )
        db.add(security_event)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enrollment failed due to internal error"
        )


@router.post("/verify", response_model=VerificationResult)
async def verify_voice(username: str,
                      request: Request,
                      audio_file: UploadFile = File(...),
                      db: Session = Depends(get_db)):
    """
    Verify user identity using voice biometrics
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Rate limiting
    rate_limit_key = f"verify_{client_ip}_{username}"
    rate_status = rate_limiter.is_rate_limited(rate_limit_key)
    if rate_status["limited"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )
        
        if not user.is_enrolled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not enrolled for voice authentication"
            )
        
        # Check if user is temporarily locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to multiple failed attempts"
            )
        
        # Read and validate audio
        audio_data = await audio_file.read()
        validation_result = security_validator.validate_audio_file(audio_data, audio_file.filename)
        
        if not validation_result["valid"]:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": validation_result["errors"]}
            )
        
        # Load audio
        try:
            audio_array, sr = librosa.load(io.BytesIO(audio_data), sr=settings.SAMPLE_RATE)
        except Exception as e:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process audio file: {str(e)}"
            )
        
        # Check audio duration
        duration = len(audio_array) / sr
        if duration < settings.MIN_AUDIO_DURATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio too short. Minimum {settings.MIN_AUDIO_DURATION} seconds required."
            )
        
        # Liveness detection (anti-spoofing)
        is_live, liveness_score = voice_processor.detect_liveness(audio_array)
        if not is_live or liveness_score < settings.LIVENESS_THRESHOLD:
            rate_limiter.record_attempt(rate_limit_key, success=False)
            
            # Log security event
            security_event = SecurityEvent(
                user_id=user.id,
                event_type="spoofing_attempt",
                severity="high",
                description=f"Liveness detection failed (score: {liveness_score:.3f})",
                ip_address=client_ip,
                additional_data=f"User-Agent: {request.headers.get('User-Agent')}"
            )
            db.add(security_event)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Liveness check failed. Please speak naturally into the microphone."
            )
        
        # Create voiceprint for verification
        verification_voiceprint, _ = voice_processor.create_voiceprint(audio_array)
        
        # Retrieve stored voiceprint
        stored_voiceprint_record = db.query(VoicePrint).filter(
            VoicePrint.user_id == user.id
        ).first()
        
        if not stored_voiceprint_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored voiceprint not found"
            )
        
        # Decrypt stored voiceprint
        stored_voiceprint = voiceprint_encryption.decrypt_voiceprint(
            stored_voiceprint_record.encrypted_features,
            str(user.id),
            stored_voiceprint_record.salt
        )
        
        # Compare voiceprints
        similarity_score = voice_processor.compare_voiceprints(
            stored_voiceprint, verification_voiceprint
        )
        
        # Determine if verification passed
        verification_passed = similarity_score >= settings.VERIFICATION_THRESHOLD
        
        if verification_passed:
            # Generate access token
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "auth_method": "voice_biometric"
            }
            access_token = auth_tokens.create_access_token(data=token_data)
            
            # Update user login info
            user.last_login = datetime.utcnow()
            user.failed_attempts = 0
            user.locked_until = None
            
            rate_limiter.record_attempt(rate_limit_key, success=True)
            
            result = VerificationResult(
                success=True,
                message="Voice verification successful!",
                confidence_score=similarity_score,
                liveness_score=liveness_score,
                user_id=str(user.id),
                access_token=access_token
            )
            
        else:
            # Handle failed verification
            user.failed_attempts += 1
            
            # Lock account after too many failures
            if user.failed_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            rate_limiter.record_attempt(rate_limit_key, success=False)
            
            result = VerificationResult(
                success=False,
                message=f"Voice verification failed. Similarity: {similarity_score:.3f}",
                confidence_score=similarity_score,
                liveness_score=liveness_score
            )
        
        # Log authentication attempt
        log_entry = AuthenticationLog(
            user_id=user.id,
            auth_type="verification",
            success=verification_passed,
            confidence_score=similarity_score,
            liveness_score=liveness_score,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        db.add(log_entry)
        db.commit()
        
        if not verification_passed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.dict()
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Log security event
        security_event = SecurityEvent(
            user_id=user.id if 'user' in locals() else None,
            event_type="verification_error",
            severity="high",
            description=f"Verification failed: {str(e)}",
            ip_address=client_ip
        )
        db.add(security_event)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed due to internal error"
        )


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile information"""
    return UserProfile(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_enrolled=current_user.is_enrolled,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status and capabilities"""
    return SystemStatus(
        status="operational",
        version=settings.PROJECT_VERSION,
        voice_engine="librosa + custom ML",
        security_features=[
            "AES-256 voiceprint encryption",
            "Liveness detection",
            "Rate limiting",
            "JWT authentication",
            "Audit logging"
        ]
    )


@router.delete("/profile/voiceprint")
async def delete_voiceprint(current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Delete user's voiceprint (GDPR compliance)"""
    try:
        # Find and delete voiceprint
        voiceprint = db.query(VoicePrint).filter(
            VoicePrint.user_id == current_user.id
        ).first()
        
        if voiceprint:
            db.delete(voiceprint)
            current_user.is_enrolled = False
            db.commit()
        
        return {
            "success": True,
            "message": "Voiceprint deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete voiceprint"
        )
