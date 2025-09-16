#!/usr/bin/env python3
"""
Simple HTTP server for the Voice Authentication System frontend
"""
import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 3000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create server
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"🌐 Voice Authentication Frontend Server")
        print(f"📱 Serving at: http://localhost:{PORT}")
        print(f"🎙️ Make sure the backend is running on http://127.0.0.1:8000")
        print(f"🚀 Opening browser...")
        print("=" * 60)
        
        # Open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
            
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🔴 Server shutting down...")
            httpd.shutdown()

if __name__ == "__main__":
    main()
