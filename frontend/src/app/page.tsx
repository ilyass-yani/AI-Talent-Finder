'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    
    if (token) {
      // Try to determine role from stored session
      const role = localStorage.getItem('user_role');
      if (role === 'recruiter') {
        router.push('/recruiter/dashboard');
      } else if (role === 'candidate') {
        router.push('/candidate/dashboard');
      } else {
        router.push('/auth/login');
      }
    } else {
      // Not logged in, redirect to login
      router.push('/auth/login');
    }
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">AI Talent Finder</h1>
        <p className="text-gray-600 mb-8">Redirige vers...</p>
        <div className="animate-spin">
          <div className="h-12 w-12 border-4 border-indigo-600 border-t-transparent rounded-full"></div>
        </div>
      </div>
    </div>
  );
}
