"use client";

import { useEffect, useState } from "react";

interface LinearProgressBarProps {
  score: number;
}

export function LinearProgressBar({ score }: LinearProgressBarProps) {
  // Initialize animatedScore from the score prop
const [animatedScore, setAnimatedScore] = useState(0);

useEffect(() => {
  let start = 0;
  const duration = 800; // animation duration in ms
  const stepTime = 16; // ~60fps
  const increment = (score - start) / (duration / stepTime);

  const animate = () => {
    start += increment;
    if ((increment > 0 && start >= score) || (increment < 0 && start <= score)) {
      setAnimatedScore(score);
      return;
    }
    setAnimatedScore(start);
    requestAnimationFrame(animate);
  };

  animate();
}, [score]);



  const getProgressColor = (score: number) => {
    if (score < 30) return "from-red-600 via-red-500 to-red-400";
    if (score < 70) return "from-yellow-500 via-orange-500 to-orange-400";
    return "from-blue-500 via-cyan-500 to-cyan-400";
  };

  const getGlowColor = (score: number) => {
    if (score < 30) return "shadow-red-500/50";
    if (score < 70) return "shadow-yellow-500/50";
    return "shadow-blue-500/50";
  };

  return (
    <div className="relative w-full">
      <div
        className={`absolute inset-0 rounded-full blur-sm ${getGlowColor(
          animatedScore
        )} bg-gradient-to-r ${getProgressColor(animatedScore)} opacity-30 animate-pulse`}
      />
      <div
        className={`absolute -inset-1 rounded-full blur-md ${getGlowColor(
          animatedScore
        )} bg-gradient-to-r ${getProgressColor(animatedScore)} opacity-20 animate-energy-pulse`}
      />

      <div className="relative h-8 bg-gray-900 rounded-full border-2 border-gray-700 overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div
            className="h-full w-full animate-slide-right"
            style={{
              backgroundImage: `repeating-linear-gradient(
                90deg,
                transparent,
                transparent 10px,
                rgba(255,255,255,0.1) 10px,
                rgba(255,255,255,0.1) 11px
              )`,
            }}
          />
        </div>

        <div
          className={`h-full bg-gradient-to-r ${getProgressColor(
            animatedScore
          )} transition-all duration-1000 ease-out relative overflow-hidden`}
          style={{ width: `${animatedScore}%` }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer-reverse" />

          <div className="absolute inset-0 flex items-center justify-around">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 h-1 bg-white rounded-full opacity-60 animate-particle"
                style={{ animationDelay: `${i * 0.3}s` }}
              />
            ))}
          </div>

          <div className="absolute top-0 right-0 w-1 h-full bg-white shadow-lg">
            <div className="absolute inset-0 bg-white animate-pulse opacity-80" />
            <div className="absolute -right-1 top-0 w-3 h-full bg-white/30 blur-sm animate-glow" />
          </div>
        </div>

        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-mono font-bold text-lg drop-shadow-lg animate-pulse">
            {animatedScore}%
          </span>
        </div>
      </div>
    </div>
  );
}
