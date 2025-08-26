import { useEffect, useState } from "react";
import GlitchText from "./GlitchText";
import "./LoadingScreen.css";

export default function LoadingScreen({ onComplete }) {
  const [showGlitch, setShowGlitch] = useState(true);

  useEffect(() => {
    // Slide in duration + delay before glitch changes
    const glitchTimeout = setTimeout(() => {
      setShowGlitch(false);
      // optional: call onComplete() after animation is fully done
      if (onComplete) onComplete();
    }, 2000); // 2 seconds for slide + glitch

    return () => clearTimeout(glitchTimeout);
  }, [onComplete]);

  return (
    <div className="loading-screen">
      <div className="loading-text">
        <span className="worth">Worth</span>
        {showGlitch ? (
          <GlitchText
            speed={1}
            enableShadows={true}
            enableOnHover={false}
            className="it-glitch"
          >
            It?
          </GlitchText>
        ) : (
          <span className="it-final">It</span>
        )}
      </div>
    </div>
  );
}
