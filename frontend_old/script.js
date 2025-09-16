// Voice Authentication System - Frontend JavaScript

class VoiceAuthApp {
    constructor() {
        this.API_BASE = 'http://127.0.0.1:8000';
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.currentAudio = null;
        this.isRecording = false;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkServerConnection();
        this.loadDashboard();
    }

    // Event Listeners Setup
    setupEventListeners() {
        // Tab Navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Forms
        document.getElementById('registerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegistration();
        });

        document.getElementById('enrollForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleEnrollment();
        });

        document.getElementById('verifyForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleVerification();
        });

        // Recording Buttons
        document.getElementById('recordBtn').addEventListener('click', () => {
            this.toggleRecording('enroll');
        });

        document.getElementById('verifyRecordBtn').addEventListener('click', () => {
            this.toggleRecording('verify');
        });

        // Re-record Buttons
        document.getElementById('rerecordBtn').addEventListener('click', () => {
            this.clearRecording('enroll');
        });

        document.getElementById('verifyRerecordBtn').addEventListener('click', () => {
            this.clearRecording('verify');
        });
    }

    // Tab Management
    switchTab(tabName) {
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        // Load dashboard data when switching to dashboard
        if (tabName === 'dashboard') {
            this.loadDashboard();
        }
    }

    // Server Connection Check
    async checkServerConnection() {
        try {
            const response = await fetch(`${this.API_BASE}/health`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateConnectionStatus('connected', 'Connected to server');
            } else {
                throw new Error('Server unhealthy');
            }
        } catch (error) {
            this.updateConnectionStatus('disconnected', 'Server disconnected');
        }
    }

    updateConnectionStatus(status, message) {
        const statusElement = document.getElementById('connectionStatus');
        statusElement.className = `status ${status}`;
        statusElement.querySelector('span').textContent = message;
    }

    // Notification System
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div>${message}</div>
            <button class="notification-close">&times;</button>
        `;

        container.appendChild(notification);

        // Auto remove
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);

        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
    }

    // User Registration
    async handleRegistration() {
        const form = document.getElementById('registerForm');
        const formData = new FormData(form);
        
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            full_name: formData.get('fullName') || null
        };

        try {
            const response = await fetch(`${this.API_BASE}/api/v1/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('✅ User registered successfully!', 'success');
                // Auto-fill username in enrollment tab
                document.getElementById('enrollUsername').value = userData.username;
                // Switch to enrollment tab
                setTimeout(() => {
                    this.switchTab('enroll');
                }, 1500);
            } else {
                throw new Error(data.detail || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showNotification(`❌ Registration failed: ${error.message}`, 'error');
        }
    }

    // Voice Recording
    async toggleRecording(type) {
        if (this.isRecording) {
            this.stopRecording(type);
        } else {
            await this.startRecording(type);
        }
    }

    async startRecording(type) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording(type);
                stream.getTracks().forEach(track => track.stop());
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // Setup audio visualization
            this.setupAudioVisualization(stream, type);
            
            // Update UI
            this.updateRecordingUI(type, true);
            
            this.showNotification('🎙️ Recording started... Speak clearly!', 'info');
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showNotification('❌ Could not access microphone. Please check permissions.', 'error');
        }
    }

    stopRecording(type) {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateRecordingUI(type, false);
            
            if (this.audioContext) {
                this.audioContext.close();
                this.audioContext = null;
            }
        }
    }

    setupAudioVisualization(stream, type) {
        const canvasId = type === 'enroll' ? 'visualizer' : 'verifyVisualizer';
        const canvas = document.getElementById(canvasId);
        const canvasContext = canvas.getContext('2d');
        
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(stream);
        
        source.connect(this.analyser);
        this.analyser.fftSize = 256;
        
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
        
        const draw = () => {
            if (!this.isRecording) return;
            
            requestAnimationFrame(draw);
            
            this.analyser.getByteFrequencyData(this.dataArray);
            
            canvasContext.fillStyle = '#f0f0f0';
            canvasContext.fillRect(0, 0, canvas.width, canvas.height);
            
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                barHeight = (this.dataArray[i] / 255) * canvas.height;
                
                const gradient = canvasContext.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                
                canvasContext.fillStyle = gradient;
                canvasContext.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }

    updateRecordingUI(type, isRecording) {
        const recordBtn = document.getElementById(type === 'enroll' ? 'recordBtn' : 'verifyRecordBtn');
        const statusElement = document.getElementById(type === 'enroll' ? 'recordingStatus' : 'verifyRecordingStatus');
        
        if (isRecording) {
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = '<i class="fas fa-stop"></i>';
            statusElement.innerHTML = '<span>🔴 Recording... Click to stop</span>';
        } else {
            recordBtn.classList.remove('recording');
            recordBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            statusElement.innerHTML = '<span>Processing recording...</span>';
        }
    }

    processRecording(type) {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.currentAudio = audioBlob;
        
        // Create audio URL for playback
        const audioUrl = URL.createObjectURL(audioBlob);
        const audioPlayer = document.getElementById(type === 'enroll' ? 'audioPlayback' : 'verifyAudioPlayback');
        const audioControls = document.getElementById(type === 'enroll' ? 'audioControls' : 'verifyAudioControls');
        const submitBtn = document.getElementById(type === 'enroll' ? 'enrollSubmitBtn' : 'verifySubmitBtn');
        const statusElement = document.getElementById(type === 'enroll' ? 'recordingStatus' : 'verifyRecordingStatus');
        
        audioPlayer.src = audioUrl;
        audioControls.style.display = 'block';
        submitBtn.disabled = false;
        
        statusElement.innerHTML = '<span>✅ Recording complete! Review and submit.</span>';
        
        this.showNotification('✅ Recording completed successfully!', 'success');
    }

    clearRecording(type) {
        this.currentAudio = null;
        
        const audioControls = document.getElementById(type === 'enroll' ? 'audioControls' : 'verifyAudioControls');
        const submitBtn = document.getElementById(type === 'enroll' ? 'enrollSubmitBtn' : 'verifySubmitBtn');
        const statusElement = document.getElementById(type === 'enroll' ? 'recordingStatus' : 'verifyRecordingStatus');
        const canvas = document.getElementById(type === 'enroll' ? 'visualizer' : 'verifyVisualizer');
        
        audioControls.style.display = 'none';
        submitBtn.disabled = true;
        statusElement.innerHTML = `<span>Click microphone to ${type === 'enroll' ? 'start recording' : 'authenticate'}</span>`;
        
        // Clear canvas
        const canvasContext = canvas.getContext('2d');
        canvasContext.fillStyle = '#f0f0f0';
        canvasContext.fillRect(0, 0, canvas.width, canvas.height);
    }

    // Voice Enrollment
    async handleEnrollment() {
        if (!this.currentAudio) {
            this.showNotification('❌ Please record your voice first', 'error');
            return;
        }

        const username = document.getElementById('enrollUsername').value;
        
        if (!username) {
            this.showNotification('❌ Please enter your username', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('username', username);
        formData.append('audio_file', this.currentAudio, 'enrollment.webm');

        try {
            this.showNotification('🔄 Processing voice enrollment...', 'info');
            
            const response = await fetch(`${this.API_BASE}/api/v1/enroll`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification(`✅ Voice enrollment successful! Quality Score: ${(data.quality_score * 100).toFixed(1)}%`, 'success');
                
                // Auto-fill username in verification tab
                document.getElementById('verifyUsername').value = username;
                
                // Switch to verification tab
                setTimeout(() => {
                    this.switchTab('verify');
                }, 2000);
                
                // Reset enrollment form
                this.clearRecording('enroll');
                
            } else {
                throw new Error(data.detail || 'Enrollment failed');
            }
        } catch (error) {
            console.error('Enrollment error:', error);
            this.showNotification(`❌ Enrollment failed: ${error.message}`, 'error');
        }
    }

    // Voice Verification
    async handleVerification() {
        if (!this.currentAudio) {
            this.showNotification('❌ Please record your voice first', 'error');
            return;
        }

        const username = document.getElementById('verifyUsername').value;
        
        if (!username) {
            this.showNotification('❌ Please enter your username', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('username', username);
        formData.append('audio_file', this.currentAudio, 'verification.webm');

        try {
            this.showNotification('🔄 Authenticating your voice...', 'info');
            
            const response = await fetch(`${this.API_BASE}/api/v1/verify`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                const confidence = (data.confidence_score * 100).toFixed(1);
                const liveness = (data.liveness_score * 100).toFixed(1);
                
                this.showNotification(
                    `🎉 Authentication Successful!\n` +
                    `Confidence: ${confidence}%\n` +
                    `Liveness: ${liveness}%\n` +
                    `Welcome back, ${username}!`, 
                    'success', 
                    7000
                );
                
                // Store token (in a real app, you'd handle this securely)
                sessionStorage.setItem('auth_token', data.access_token);
                sessionStorage.setItem('user_id', data.user_id);
                
                // Reset verification form
                this.clearRecording('verify');
                
                // Switch to dashboard
                setTimeout(() => {
                    this.switchTab('dashboard');
                    this.loadDashboard();
                }, 2000);
                
            } else {
                if (response.status === 401) {
                    const confidence = data.detail?.confidence_score ? (data.detail.confidence_score * 100).toFixed(1) : 'Unknown';
                    this.showNotification(`❌ Authentication Failed!\nConfidence: ${confidence}%\nPlease try again.`, 'error');
                } else {
                    throw new Error(data.detail || 'Verification failed');
                }
            }
        } catch (error) {
            console.error('Verification error:', error);
            this.showNotification(`❌ Verification failed: ${error.message}`, 'error');
        }
    }

    // Dashboard
    async loadDashboard() {
        try {
            // Load system status
            const statusResponse = await fetch(`${this.API_BASE}/api/v1/status`);
            const statusData = await statusResponse.json();
            
            if (statusResponse.ok) {
                this.updateSystemStatus(statusData);
            }
            
            // Load health check
            const healthResponse = await fetch(`${this.API_BASE}/health`);
            const healthData = await healthResponse.json();
            
            if (healthResponse.ok) {
                this.updateHealthStatus(healthData);
            }
            
        } catch (error) {
            console.error('Dashboard error:', error);
            this.showNotification('❌ Failed to load dashboard data', 'error');
        }
    }

    updateSystemStatus(data) {
        const statusContainer = document.getElementById('systemStatus');
        
        statusContainer.innerHTML = `
            <div class="status-item">
                <i class="fas fa-server"></i>
                <div>
                    <strong>System Status</strong>
                    <br><span>${data.status || 'Unknown'}</span>
                </div>
            </div>
            <div class="status-item">
                <i class="fas fa-cog"></i>
                <div>
                    <strong>Voice Engine</strong>
                    <br><span>${data.voice_engine || 'Unknown'}</span>
                </div>
            </div>
            <div class="status-item">
                <i class="fas fa-shield-alt"></i>
                <div>
                    <strong>Security</strong>
                    <br><span>${data.security_features ? data.security_features.length : 0} features active</span>
                </div>
            </div>
        `;
    }

    updateHealthStatus(data) {
        const statusContainer = document.getElementById('systemStatus');
        const existingContent = statusContainer.innerHTML;
        
        statusContainer.innerHTML = existingContent + `
            <div class="status-item">
                <i class="fas fa-heartbeat"></i>
                <div>
                    <strong>Health Status</strong>
                    <br><span>${data.status || 'Unknown'}</span>
                </div>
            </div>
        `;
        
        // Update activity list
        const activityList = document.getElementById('activityList');
        const now = new Date().toLocaleString();
        
        activityList.innerHTML = `
            <div class="activity-item">
                <strong>System Check</strong> - ${now}
                <br><small>All systems operational</small>
            </div>
            <div class="activity-item">
                <strong>Dashboard Loaded</strong> - ${now}
                <br><small>Interface ready for use</small>
            </div>
        `;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VoiceAuthApp();
});
