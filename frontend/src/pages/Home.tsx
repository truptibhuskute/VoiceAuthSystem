import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Shield, Mic, Lock, Zap, Users, CheckCircle } from 'lucide-react';

const Home: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white">
        <div className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            <Shield className="h-16 w-16 mx-auto mb-8 text-primary-100" />
            <h1 className="text-5xl font-bold mb-6">
              Voice Authentication System
            </h1>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Secure, fast, and convenient biometric authentication using your unique voice signature. 
              Experience the future of passwordless security.
            </p>
            
            {!isAuthenticated ? (
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/register"
                  className="bg-white text-primary-600 hover:bg-primary-50 px-8 py-3 rounded-lg font-semibold transition-colors"
                >
                  Get Started
                </Link>
                <Link
                  to="/verify"
                  className="border-2 border-white text-white hover:bg-white hover:text-primary-600 px-8 py-3 rounded-lg font-semibold transition-colors"
                >
                  Try Voice Login
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-lg text-primary-100">
                  Welcome back, {user?.full_name || user?.username}!
                </p>
                <Link
                  to="/dashboard"
                  className="inline-block bg-white text-primary-600 hover:bg-primary-50 px-8 py-3 rounded-lg font-semibold transition-colors"
                >
                  Go to Dashboard
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Why Choose Voice Authentication?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Advanced biometric security that's both highly secure and incredibly convenient
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <div className="text-center p-8 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
              <Lock className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-3">Highly Secure</h3>
              <p className="text-gray-600">
                Your voice is as unique as your fingerprint. Our advanced algorithms create an encrypted voiceprint that's nearly impossible to replicate.
              </p>
            </div>
            
            <div className="text-center p-8 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
              <Zap className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-3">Lightning Fast</h3>
              <p className="text-gray-600">
                Authenticate in seconds with just your voice. No more forgotten passwords or waiting for SMS codes.
              </p>
            </div>
            
            <div className="text-center p-8 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
              <Users className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-3">User Friendly</h3>
              <p className="text-gray-600">
                Simple and intuitive. Just speak naturally - no special phrases or training required.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600">
              Get started with voice authentication in three simple steps
            </p>
          </div>
          
          <div className="max-w-4xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="bg-primary-600 text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                  1
                </div>
                <h3 className="text-xl font-semibold mb-3">Sign Up</h3>
                <p className="text-gray-600">
                  Create your account with basic information and a secure password.
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-primary-600 text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                  2
                </div>
                <Mic className="h-8 w-8 text-primary-600 mx-auto mb-3" />
                <h3 className="text-xl font-semibold mb-3">Enroll Your Voice</h3>
                <p className="text-gray-600">
                  Record a short voice sample to create your unique biometric profile.
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-primary-600 text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                  3
                </div>
                <CheckCircle className="h-8 w-8 text-primary-600 mx-auto mb-3" />
                <h3 className="text-xl font-semibold mb-3">Start Using</h3>
                <p className="text-gray-600">
                  Login instantly using just your voice. Fast, secure, and convenient.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      {!isAuthenticated && (
        <div className="py-20 bg-primary-600 text-white">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Experience Voice Authentication?
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Join thousands of users who have already switched to secure voice authentication.
            </p>
            <Link
              to="/register"
              className="bg-white text-primary-600 hover:bg-primary-50 px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
            >
              Get Started Today
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
