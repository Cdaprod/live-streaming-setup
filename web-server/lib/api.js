// lib/api.js
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchApi(endpoint, options = {}) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.message || 'An error occurred');
  }

  return res.json();
}

export function getWebSocketUrl() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return process.env.NEXT_PUBLIC_WS_URL || 
    `${wsProtocol}//${window.location.hostname}:8000/ws`;
}