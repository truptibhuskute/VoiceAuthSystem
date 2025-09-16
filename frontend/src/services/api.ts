import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for audio uploads
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_data');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  is_enrolled: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface VerificationResult {
  success: boolean;
  confidence_score: number;
  liveness_score: number;
  user_id?: string;
  message: string;
}

export interface EnrollmentResult {
  success: boolean;
  quality_score: number;
  message: string;
}

// API Functions
export const authAPI = {
  register: async (userData: RegisterRequest): Promise<AxiosResponse<User>> =>
    apiClient.post('/auth/register', userData),

  login: async (username: string, password: string): Promise<AxiosResponse<LoginResponse>> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    return apiClient.post('/auth/token', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  getCurrentUser: async (): Promise<AxiosResponse<User>> =>
    apiClient.get('/users/me'),
};

export const voiceAPI = {
  enroll: async (audioBlob: Blob): Promise<AxiosResponse<EnrollmentResult>> => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'enrollment.wav');
    
    return apiClient.post('/voice/enroll', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  verify: async (audioBlob: Blob): Promise<AxiosResponse<VerificationResult>> => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'verification.wav');
    
    return apiClient.post('/voice/verify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  verifyAnonymous: async (audioBlob: Blob): Promise<AxiosResponse<VerificationResult>> => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'verification.wav');
    
    return apiClient.post('/voice/verify-anonymous', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export const userAPI = {
  getProfile: async (): Promise<AxiosResponse<User>> =>
    apiClient.get('/users/profile'),

  updateProfile: async (profileData: Partial<User>): Promise<AxiosResponse<User>> =>
    apiClient.put('/users/profile', profileData),
};

export const systemAPI = {
  getHealth: async (): Promise<AxiosResponse<{ status: string; timestamp: string }>> =>
    apiClient.get('/system/health'),

  getStatus: async (): Promise<AxiosResponse<{ 
    status: string; 
    version: string; 
    users_count: number; 
    enrollments_count: number; 
  }>> =>
    apiClient.get('/system/status'),
};

export default apiClient;
