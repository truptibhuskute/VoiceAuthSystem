"""
Advanced Voice Processing Engine for Biometric Authentication

This module handles:
1. Audio preprocessing and normalization
2. Feature extraction (MFCC, spectral features)
3. Voice quality assessment
4. Anti-spoofing detection
5. Similarity matching
"""

import numpy as np
import librosa
import scipy.signal
from typing import Dict, Tuple, Optional, Any
import hashlib
import json
from datetime import datetime


class VoiceProcessor:
    """
    Advanced voice processing engine for biometric authentication
    """
    
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 40):
        """
        Initialize the voice processor
        
        Args:
            sample_rate: Audio sample rate in Hz
            n_mfcc: Number of MFCC coefficients to extract
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.hop_length = 512
        self.n_fft = 2048
        
        # Pre-emphasis filter coefficient
        self.pre_emphasis = 0.97
        
        # Voice activity detection parameters
        self.vad_threshold = 0.01
        self.min_speech_duration = 0.5  # seconds
        
    def preprocess_audio(self, audio: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Preprocess raw audio for feature extraction
        
        Args:
            audio: Raw audio signal
            
        Returns:
            Preprocessed audio and metadata
        """
        metadata = {}
        
        # Normalize audio
        if len(audio) == 0:
            raise ValueError("Empty audio signal")
            
        # Apply pre-emphasis filter
        audio = np.append(audio[0], audio[1:] - self.pre_emphasis * audio[:-1])
        
        # Normalize amplitude
        audio = audio / np.max(np.abs(audio))
        
        # Voice Activity Detection (VAD)
        frame_length = int(0.025 * self.sample_rate)  # 25ms frames
        hop_length = int(0.01 * self.sample_rate)     # 10ms hop
        
        # Calculate energy for each frame
        frames = librosa.util.frame(audio, frame_length=frame_length, 
                                   hop_length=hop_length, axis=0)
        energy = np.sum(frames ** 2, axis=0)
        
        # Find speech segments
        speech_frames = energy > (self.vad_threshold * np.max(energy))
        
        if np.sum(speech_frames) < (self.min_speech_duration * self.sample_rate / hop_length):
            metadata['warning'] = 'Insufficient speech content detected'
        
        metadata.update({
            'duration': len(audio) / self.sample_rate,
            'speech_ratio': np.sum(speech_frames) / len(speech_frames),
            'max_amplitude': np.max(np.abs(audio)),
            'energy_variance': np.var(energy)
        })
        
        return audio, metadata
    
    def extract_mfcc_features(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features from audio
        
        Args:
            audio: Preprocessed audio signal
            
        Returns:
            MFCC feature matrix
        """
        # Extract MFCC features
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window='hann'
        )
        
        # Apply delta and delta-delta features
        delta_mfcc = librosa.feature.delta(mfcc)
        delta2_mfcc = librosa.feature.delta(mfcc, order=2)
        
        # Concatenate all features
        features = np.vstack([mfcc, delta_mfcc, delta2_mfcc])
        
        return features
    
    def extract_spectral_features(self, audio: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extract additional spectral features for enhanced security
        
        Args:
            audio: Preprocessed audio signal
            
        Returns:
            Dictionary of spectral features
        """
        features = {}
        
        # Spectral centroid
        features['spectral_centroid'] = librosa.feature.spectral_centroid(
            y=audio, sr=self.sample_rate)[0]
        
        # Spectral rolloff
        features['spectral_rolloff'] = librosa.feature.spectral_rolloff(
            y=audio, sr=self.sample_rate)[0]
        
        # Spectral bandwidth
        features['spectral_bandwidth'] = librosa.feature.spectral_bandwidth(
            y=audio, sr=self.sample_rate)[0]
        
        # Zero crossing rate
        features['zero_crossing_rate'] = librosa.feature.zero_crossing_rate(audio)[0]
        
        # Chroma features
        features['chroma'] = librosa.feature.chroma_stft(
            y=audio, sr=self.sample_rate)
        
        # Fundamental frequency (F0)
        f0 = librosa.piptrack(y=audio, sr=self.sample_rate, threshold=0.1)[0]
        features['f0'] = np.max(f0, axis=0)
        
        return features
    
    def create_voiceprint(self, audio: np.ndarray) -> Tuple[Dict[str, Any], float]:
        """
        Create a comprehensive voiceprint from audio
        
        Args:
            audio: Raw audio signal
            
        Returns:
            Voiceprint dictionary and quality score
        """
        # Preprocess audio
        processed_audio, metadata = self.preprocess_audio(audio)
        
        # Extract MFCC features
        mfcc_features = self.extract_mfcc_features(processed_audio)
        
        # Extract spectral features
        spectral_features = self.extract_spectral_features(processed_audio)
        
        # Calculate statistical measures for MFCC
        mfcc_stats = {
            'mean': np.mean(mfcc_features, axis=1),
            'std': np.std(mfcc_features, axis=1),
            'min': np.min(mfcc_features, axis=1),
            'max': np.max(mfcc_features, axis=1)
        }
        
        # Calculate quality score based on various factors
        quality_score = self._calculate_quality_score(metadata, mfcc_features, spectral_features)
        
        # Create voiceprint
        voiceprint = {
            'mfcc_stats': mfcc_stats,
            'spectral_features': {k: np.mean(v) if len(v.shape) > 0 else v 
                                for k, v in spectral_features.items()},
            'metadata': metadata,
            'feature_version': '1.0',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return voiceprint, quality_score
    
    def _calculate_quality_score(self, metadata: Dict, mfcc: np.ndarray, 
                                spectral: Dict[str, np.ndarray]) -> float:
        """
        Calculate voice quality score for enrollment
        
        Args:
            metadata: Audio metadata
            mfcc: MFCC features
            spectral: Spectral features
            
        Returns:
            Quality score between 0 and 1
        """
        score = 1.0
        
        # Penalize low speech ratio
        if metadata['speech_ratio'] < 0.6:
            score *= 0.7
            
        # Penalize very short duration
        if metadata['duration'] < 2.0:
            score *= 0.8
            
        # Penalize low energy variance (monotone speech)
        if metadata['energy_variance'] < 0.01:
            score *= 0.6
            
        # Check MFCC feature variance (uniqueness)
        mfcc_variance = np.mean(np.var(mfcc, axis=1))
        if mfcc_variance < 10.0:
            score *= 0.8
            
        # Check spectral diversity
        spectral_centroid_var = np.var(spectral['spectral_centroid'])
        if spectral_centroid_var < 1000:
            score *= 0.9
            
        return max(0.0, min(1.0, score))
    
    def compare_voiceprints(self, voiceprint1: Dict[str, Any], 
                           voiceprint2: Dict[str, Any]) -> float:
        """
        Compare two voiceprints and return similarity score
        
        Args:
            voiceprint1: First voiceprint
            voiceprint2: Second voiceprint
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract MFCC statistics
        mfcc1 = voiceprint1['mfcc_stats']
        mfcc2 = voiceprint2['mfcc_stats']
        
        # Calculate cosine similarity for MFCC means
        mean_similarity = self._cosine_similarity(mfcc1['mean'], mfcc2['mean'])
        
        # Calculate correlation for standard deviations
        std_correlation = np.corrcoef(mfcc1['std'], mfcc2['std'])[0, 1]
        if np.isnan(std_correlation):
            std_correlation = 0.0
            
        # Compare spectral features
        spectral1 = voiceprint1['spectral_features']
        spectral2 = voiceprint2['spectral_features']
        
        spectral_similarities = []
        for feature in ['spectral_centroid', 'spectral_rolloff', 'spectral_bandwidth']:
            if feature in spectral1 and feature in spectral2:
                sim = 1.0 - abs(spectral1[feature] - spectral2[feature]) / \
                      (abs(spectral1[feature]) + abs(spectral2[feature]) + 1e-8)
                spectral_similarities.append(sim)
        
        spectral_sim = np.mean(spectral_similarities) if spectral_similarities else 0.5
        
        # Weighted combination
        final_similarity = (0.6 * mean_similarity + 0.2 * abs(std_correlation) + 
                          0.2 * spectral_sim)
        
        return max(0.0, min(1.0, final_similarity))
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
    
    def detect_liveness(self, audio: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if audio is from a live speaker or a recording/synthetic source
        
        Args:
            audio: Raw audio signal
            
        Returns:
            (is_live, confidence_score)
        """
        # This is a simplified liveness detection
        # In production, you'd use more sophisticated methods
        
        processed_audio, metadata = self.preprocess_audio(audio)
        
        # Check for signs of recording artifacts
        liveness_score = 1.0
        
        # 1. Check for unnatural frequency patterns
        freqs, times, stft = scipy.signal.stft(processed_audio, self.sample_rate)
        magnitude = np.abs(stft)
        
        # Look for suspicious frequency patterns
        freq_entropy = -np.sum(magnitude * np.log(magnitude + 1e-8), axis=0)
        avg_entropy = np.mean(freq_entropy)
        
        if avg_entropy < 5.0:  # Too uniform, possibly synthetic
            liveness_score *= 0.6
            
        # 2. Check for micro-variations in pitch (natural human speech)
        # Extract F0 from spectral features if available, otherwise skip this check
        spectral_features = self.extract_spectral_features(processed_audio)
        f0_values = spectral_features.get('f0', np.array([0]))
        f0_variation = np.std(f0_values) if len(f0_values) > 1 else 0
        if f0_variation < 10.0:  # Too stable, possibly synthetic
            liveness_score *= 0.7
            
        # 3. Check for natural breathing patterns and pauses
        if metadata['speech_ratio'] > 0.95:  # Too much continuous speech
            liveness_score *= 0.8
            
        # 4. Check amplitude variations (natural microphone distance changes)
        if metadata['energy_variance'] < 0.005:  # Too stable amplitude
            liveness_score *= 0.7
            
        is_live = liveness_score > 0.7
        
        return is_live, liveness_score
    
    def generate_feature_hash(self, voiceprint: Dict[str, Any]) -> str:
        """
        Generate a hash of the voiceprint for integrity checking
        
        Args:
            voiceprint: Voiceprint dictionary
            
        Returns:
            SHA-256 hash of the features
        """
        # Create a deterministic string representation of key features
        feature_string = json.dumps({
            'mfcc_mean': voiceprint['mfcc_stats']['mean'].tolist(),
            'mfcc_std': voiceprint['mfcc_stats']['std'].tolist(),
            'spectral_features': voiceprint['spectral_features'],
            'feature_version': voiceprint['feature_version']
        }, sort_keys=True)
        
        return hashlib.sha256(feature_string.encode()).hexdigest()
