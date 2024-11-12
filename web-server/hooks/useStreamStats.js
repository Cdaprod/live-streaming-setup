// web-server/hooks/useStreamStats.js
import { useState, useEffect } from 'react';

export const useStreamStats = () => {
  const [streamStats, setStreamStats] = useState({
    isLive: false,
    duration: 0,
    bitrate: 0,
    resolution: '',
    fps: 0,
    quality: 100
  });

  const [qualityAlerts, setQualityAlerts] = useState([]);
  const [recordings, setRecordings] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Update stream stats
      if (data.type === 'stats') {
        setStreamStats(prev => ({
          ...prev,
          isLive: data.isLive,
          duration: data.duration,
          bitrate: data.bitrate,
          resolution: data.resolution,
          fps: data.fps,
          quality: data.quality
        }));
      }
      
      // Update quality alerts
      if (data.type === 'alerts') {
        setQualityAlerts(data.alerts);
      }
      
      // Update recordings
      if (data.type === 'recordings') {
        setRecordings(data.recordings);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, []);

  const startRecording = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/recording/start', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to start recording');
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/recording/stop', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to stop recording');
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  };

  const createClip = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/clip/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          duration: 30 // Default 30 second clip
        }),
      });
      if (!response.ok) throw new Error('Failed to create clip');
    } catch (error) {
      console.error('Error creating clip:', error);
    }
  };

  return {
    streamStats,
    qualityAlerts,
    recordings,
    startRecording,
    stopRecording,
    createClip
  };
};