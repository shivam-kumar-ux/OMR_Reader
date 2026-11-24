import React, { useRef, useState, useEffect } from 'react';
import { Camera, RefreshCw, AlertCircle, CheckCircle2, VideoOff } from 'lucide-react';

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  disabled?: boolean;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({ onCapture, disabled }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [qualityFeedback, setQualityFeedback] = useState<{
    brightness: 'OK' | 'DARK' | 'GLARE';
    blur: 'OK' | 'BLUR';
  }>({ brightness: 'OK', blur: 'OK' });

  const startCamera = async () => {
    setCameraError(null);
    try {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err: any) {
      setCameraError(err.message || 'Unable to access camera device');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  // Frame quality monitor
  useEffect(() => {
    if (!stream) return;
    const interval = setInterval(() => {
      if (!videoRef.current || !canvasRef.current || videoRef.current.readyState < 2) return;
      const v = videoRef.current;
      const c = canvasRef.current;
      c.width = 160;
      c.height = 120;
      const ctx = c.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(v, 0, 0, 160, 120);
      const imgData = ctx.getImageData(0, 0, 160, 120);
      const data = imgData.data;

      let sumLum = 0;
      let saturatedCount = 0;
      const totalPixels = data.length / 4;

      for (let i = 0; i < data.length; i += 4) {
        const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        sumLum += lum;
        if (lum > 250) saturatedCount++;
      }

      const avgLum = sumLum / totalPixels;
      const satRatio = saturatedCount / totalPixels;

      let bStatus: 'OK' | 'DARK' | 'GLARE' = 'OK';
      if (avgLum < 55) bStatus = 'DARK';
      else if (satRatio > 0.25 || avgLum > 245) bStatus = 'GLARE';

      setQualityFeedback({
        brightness: bStatus,
        blur: 'OK',
      });
    }, 600);

    return () => clearInterval(interval);
  }, [stream]);

  const handleCapture = () => {
    if (!videoRef.current) return;
    const v = videoRef.current;
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = v.videoWidth || 1920;
    captureCanvas.height = v.videoHeight || 1080;
    const ctx = captureCanvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, captureCanvas.width, captureCanvas.height);

    captureCanvas.toBlob(blob => {
      if (blob) {
        const file = new File([blob], `camera_scan_${Date.now()}.jpg`, { type: 'image/jpeg' });
        onCapture(file);
      }
    }, 'image/jpeg', 0.95);
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full max-w-2xl bg-black rounded-xl overflow-hidden shadow-lg border border-slate-700 aspect-[4/3]">
        {cameraError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center text-slate-300">
            <VideoOff className="w-12 h-12 text-rose-500 mb-3" />
            <p className="font-semibold text-white">Camera Access Error</p>
            <p className="text-sm mt-1 max-w-md text-slate-400">{cameraError}</p>
            <button
              onClick={startCamera}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" /> Try Again
            </button>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            <canvas ref={canvasRef} className="hidden" />

            {/* On-Screen Alignment Guide Frame */}
            <div className="absolute inset-8 border-2 border-dashed border-emerald-400/80 rounded-lg pointer-events-none flex flex-col justify-between p-4">
              {/* 4 Corner Markers Guide */}
              <div className="flex justify-between">
                <div className="w-8 h-8 border-t-4 border-l-4 border-emerald-400"></div>
                <div className="w-8 h-8 border-t-4 border-r-4 border-emerald-400"></div>
              </div>
              <div className="text-center bg-black/60 backdrop-blur-sm text-emerald-300 text-xs px-3 py-1 rounded-full mx-auto font-medium">
                Align the 4 sheet corner squares inside this frame
              </div>
              <div className="flex justify-between">
                <div className="w-8 h-8 border-b-4 border-l-4 border-emerald-400"></div>
                <div className="w-8 h-8 border-b-4 border-r-4 border-emerald-400"></div>
              </div>
            </div>

            {/* Live Quality Status Pills */}
            <div className="absolute top-3 left-3 flex gap-2">
              <div className={`px-2.5 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 shadow-sm ${
                qualityFeedback.brightness === 'OK'
                  ? 'bg-emerald-900/80 text-emerald-200 border border-emerald-700'
                  : 'bg-amber-900/80 text-amber-200 border border-amber-700'
              }`}>
                {qualityFeedback.brightness === 'OK' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                {qualityFeedback.brightness === 'OK' ? 'Lighting Good' : qualityFeedback.brightness === 'DARK' ? 'Too Dark' : 'Glare Detected'}
              </div>
            </div>
          </>
        )}
      </div>

      <div className="mt-4 flex items-center gap-4">
        <button
          onClick={handleCapture}
          disabled={disabled || !!cameraError}
          className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow flex items-center gap-2 text-base transition-all active:scale-95"
        >
          <Camera className="w-5 h-5" /> Capture & Process Sheet
        </button>
      </div>
    </div>
  );
};
