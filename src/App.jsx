import { useRef, useEffect, useState } from 'react';
import DarkVeil from './components/DarkVeil';
import amazonLogo from './assets/amazon.png';
import flipkartLogo from './assets/flipkart.png';
import cromaLogo from './assets/croma.png';
import relianceLogo from './assets/reliance.png';
import ProductInput from './components/ProductInput';
import { productSuggestions } from './data/productSuggestions';
import SearchButton from './components/SearchButton';
import gsap from 'gsap';

// ---------------- LinearProgressBar ----------------
export function LinearProgressBar({ score }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const currentRef = useRef(0);
  const [visible, setVisible] = useState(false); // fade-in state

  useEffect(() => {
    if (score > 0) setVisible(true); // show bar only when score is calculated

    let start = currentRef.current; // start from current value
    const end = Math.min(score, 100); // Capped at 100
    const duration = 800; // ms
    const startTime = performance.now();

    const animate = (time) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const newVal = start + (end - start) * progress;

      setAnimatedScore(newVal);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        currentRef.current = end; // save final
      }
    };

    requestAnimationFrame(animate);
  }, [score]);

  const getProgressColor = (val) => {
    if (val < 30) return "from-red-600 via-red-500 to-red-400";
    if (val < 70) return "from-yellow-500 via-orange-500 to-orange-400";
    return "from-blue-500 via-cyan-500 to-cyan-400";
  };

  const getGlowColor = (val) => {
    if (val < 30) return "shadow-red-500/50";
    if (val < 70) return "shadow-yellow-500/50";
    return "shadow-blue-500/50";
  };

  return (
    <div
      className={`relative w-full transition-opacity duration-1000 ease-out ${visible ? 'opacity-100' : 'opacity-0'}`}
    >
      {/* Glow layers */}
      <div className={`absolute inset-0 rounded-full blur-sm ${getGlowColor(animatedScore)} bg-gradient-to-r ${getProgressColor(animatedScore)} opacity-30 animate-pulse`} />
      <div className={`absolute -inset-1 rounded-full blur-md ${getGlowColor(animatedScore)} bg-gradient-to-r ${getProgressColor(animatedScore)} opacity-20 animate-energy-pulse`} />

      {/* Bar container */}
      <div className="relative h-8 bg-gray-900 rounded-full border-2 border-gray-700 overflow-hidden">
        {/* Moving stripes */}
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

        {/* Progress fill */}
        <div
          className={`h-full bg-gradient-to-r ${getProgressColor(animatedScore)} transition-all duration-1000 ease-out relative overflow-hidden`}
          style={{ width: `${animatedScore}%` }}
        >
          {/* Shimmer layers */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer-reverse" />

          {/* Particle sparks */}
          <div className="absolute inset-0 flex items-center justify-around">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 h-1 bg-white rounded-full opacity-60 animate-particle"
                style={{ animationDelay: `${i * 0.3}s` }}
              />
            ))}
          </div>

          {/* Front glow */}
          <div className="absolute top-0 right-0 w-1 h-full bg-white shadow-lg">
            <div className="absolute inset-0 bg-white animate-pulse opacity-80" />
            <div className="absolute -right-1 top-0 w-3 h-full bg-white/30 blur-sm animate-glow" />
          </div>
        </div>

        {/* Score label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="text-white font-mono font-bold text-lg drop-shadow-lg animate-pulse"
            style={{ textShadow: '1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000' }}
          >
            {Math.round(animatedScore)}%
          </span>
        </div>
      </div>
    </div>
  );
}
// ---------------- End LinearProgressBar ----------------
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

// ---------------- Fixed SplashOverlay (fade-in works now) ----------------
function SplashOverlay({ visible, rowsLoaded, onHide }) {
  const [stage, setStage] = useState('hidden'); // hidden, fadeIn, glow, logoHold, logoUp, messageIn, messageOut, fadeOut
  const [sequenceDone, setSequenceDone] = useState(false);
  const rowsArrivedRef = useRef(false);
  const tRef = useRef([]);

  useEffect(() => {
    const clearTimers = () => {
      tRef.current.forEach((id) => clearTimeout(id));
      tRef.current = [];
    };

    if (!visible) {
      // If overlay was visible, trigger fadeOut
      if (stage !== 'hidden') setStage('fadeOut');
      return clearTimers;
    }

    // When visible becomes true -> start sequence beginning with fadeIn
    setStage('fadeIn'); // important: we set this AFTER the component has been painted once at opacity:0
    setSequenceDone(false);
    rowsArrivedRef.current = rowsLoaded;

    const fadeInDur = 600;
    const glowDur = 2000;
    const logoHoldDur = 1500;
    const logoUpDur = 1000;
    const messageInDur = 480;
    const messageHoldDur = 1200;
    const messageOutDur = 420;

    const fadeInDelay = 100; // slight delay for smooth effect

    tRef.current.push(setTimeout(() => setStage('glow'), fadeInDur + fadeInDelay));
    tRef.current.push(setTimeout(() => setStage('logoHold'), fadeInDur + fadeInDelay + glowDur));
    tRef.current.push(setTimeout(() => setStage('logoUp'), fadeInDur + fadeInDelay + glowDur + logoHoldDur));
    tRef.current.push(setTimeout(() => setStage('messageIn'), fadeInDur + fadeInDelay + glowDur + logoHoldDur + logoUpDur));
    tRef.current.push(setTimeout(() => setStage('messageOut'),
      fadeInDur + fadeInDelay + glowDur + logoHoldDur + logoUpDur + messageInDur + messageHoldDur
    ));
    tRef.current.push(setTimeout(() => {
      setSequenceDone(true);
      if (rowsArrivedRef.current) setStage('fadeOut');
      else setStage('waiting');
    },
      fadeInDur + fadeInDelay + glowDur + logoHoldDur + logoUpDur + messageInDur + messageHoldDur + messageOutDur
    ));

    return () => clearTimers();
  }, [visible]);

  useEffect(() => {
    if (!visible) return;
    rowsArrivedRef.current = !!rowsLoaded;
    if (sequenceDone && rowsArrivedRef.current) {
      tRef.current.push(setTimeout(() => setStage('fadeOut'), 180));
    }
  }, [rowsLoaded, sequenceDone, visible]);

  // When fadeOut finishes, fully hide and notify parent
  useEffect(() => {
    if (stage !== 'fadeOut') return;
    const id = setTimeout(() => {
      setStage('hidden');
      setSequenceDone(false);
      rowsArrivedRef.current = false;
      onHide && onHide();
    }, 600); // match the CSS transition duration for opacity
    return () => clearTimeout(id);
  }, [stage, onHide]);

  // Stage helpers
  const logoGlowOn = ['glow', 'logoHold'].includes(stage);
  const logoHold = stage === 'logoHold';
  const logoGone = ['logoUp', 'messageIn', 'messageOut', 'waiting', 'fadeOut'].includes(stage);
  const messageIn = stage === 'messageIn';
  const messageOut = stage === 'messageOut';
  const showSpinner = stage === 'waiting' || (stage === 'messageOut' && !rowsLoaded);

  // Important: DO NOT return null here. Always render the overlay element.
  // Control visibility via opacity/visibility/pointerEvents so it doesn't block input when hidden.
  const isVisibleNow = stage !== 'hidden'; // if hidden, keep opacity 0 but still render so fade-in can occur
  const isOpaque = stage !== 'hidden' && stage !== 'fadeOut' ? 1 : 0;

  return (
    <div
      aria-hidden
      className={`curtain-overlay ${stage === 'fadeOut' ? 'fade-out' : (stage === 'fadeIn' ? 'fade-in' : '')}`}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        // make sure overlay doesn't block pointer events when fully hidden/fading out
        pointerEvents: isOpaque ? 'all' : 'none',
        backgroundColor: 'black',
        // opacity animated between 0 and 1
        opacity: isOpaque,
        transition: 'opacity 0.6s ease',
        // keep the element in layout but non-interactive when 'hidden' to allow fade-in on next tick
        visibility: isVisibleNow ? 'visible' : 'hidden',
      }}
    >
      <div className="splash-column" style={{ textAlign: 'center' }}>
        <div 
          className={`splash-logo ${logoGlowOn ? 'glow' : ''} ${logoHold ? 'hold' : ''} ${logoGone ? 'up' : ''}`} 
          style={{ marginTop: '-90px', marginLeft: '-20px' }} // ✅ moved here
        >
          <span style={{ color: 'black', WebkitTextStroke: '2px white' }}>Worth</span>
          <span style={{ color: 'black', WebkitTextStroke: '2px white' }}>It</span>
        </div>

        <div className={`splash-message ${messageIn ? 'in' : ''} ${messageOut ? 'out' : ''}`}>
          Making shopping easier and cheaper!
        </div>

        {showSpinner && (
          <div className="buffer-spinner" role="status" aria-live="polite" aria-label="Loading results">
            <div style={{ display: 'flex', gap: '10px' }}>
              <div className="buffer-dot" />
              <div className="buffer-dot" />
            </div>
          </div>
        )}
      </div>

      <style>{`
        .splash-column { display:flex; flex-direction:column; align-items:center; justify-content:center; gap: 1rem; pointer-events: none; }
        .splash-logo { font-weight:900; font-style:italic; font-size:clamp(4rem,12vw,9rem); color:black; -webkit-text-stroke:2px white; transition: transform 0.6s ease, opacity 0.6s ease, filter 2s ease; filter: drop-shadow(0 0 0 rgba(255,255,255,0)); }
        .splash-logo.glow { animation: glowPulse 2s forwards; }
        @keyframes glowPulse { 0% { filter: drop-shadow(0 0 0 rgba(255,255,255,0)); } 100% { filter: drop-shadow(0 0 28px rgba(255,255,255,0.95)); } }
        .splash-logo.hold { opacity:1; transform: translateY(0) scale(1); }
        .splash-logo.up { 
            transform: translateY(-160px) scale(0.92); 
            opacity: 0; 
            transition: transform 1s cubic-bezier(0.22, 1, 0.36, 1), opacity 1s ease; 
          }
        .splash-message { color:white; font-style:italic; font-weight:600; font-size:clamp(1rem,3vw,2rem); margin-top:-10rem; opacity:0; transform:translateY(60px); transition: transform 480ms cubic-bezier(.2,.9,.3,1), opacity 420ms ease; text-align:center; }
        .splash-message.in { opacity:1; transform:translateY(0); }
        .splash-message.out { opacity:0; transform:translateY(-30px); }
        .buffer-spinner { width:80px; height:80px; border-radius:999px; display:grid; place-items:center; margin-top:1.5rem; }
        .buffer-dot { width:12px; height:12px; border-radius:50%; background:white; opacity:0.95; animation: bufferJump 0.9s infinite ease-in-out; }
        .buffer-dot:nth-child(2){ animation-delay:0.15s } .buffer-dot:nth-child(3){ animation-delay:0.3s }
        @keyframes bufferJump { 0% { transform: translateY(0); opacity:0.6 } 50% { transform: translateY(-18px); opacity:1 } 100% { transform: translateY(0); opacity:0.6 } }
      `}</style>
    </div>
  );
}
// ---------------- end SplashOverlay ----------------



// StarField
function StarField() {
  const canvasRef = useRef(null);
  const stars = useRef([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animationId;
    let width, height;

    const resize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const createStar = () => ({
      x: Math.random() * width,
      y: height + Math.random() * 100,
      size: Math.random() * 1.5 + 0.5,
      speed: Math.random() * 0.5 + 0.3,
      alpha: 1,
    });

    for (let i = 0; i < 80; i++) stars.current.push(createStar());

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      for (let star of stars.current) {
        star.y -= star.speed;
        if (star.y < height / 2) star.alpha -= 0.01;

        ctx.beginPath();
        ctx.fillStyle = `rgba(255, 255, 255, ${star.alpha})`;
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();

        if (star.alpha <= 0 || star.y < -10) Object.assign(star, createStar());
      }
      animationId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}

// Input Logo (home)
function InputLogo({ show }) {
  return (
    <div
      style={{
        position: 'absolute',
        top: '60px',
        fontSize: 'clamp(2rem, 8vw, 5rem)',
        fontWeight: 900,
        fontStyle: 'italic',
        display: 'flex',
        alignItems: 'center',
        color: 'white',
        opacity: show ? 1 : 0,
        transition: 'opacity 1s ease, transform 1s ease',
        transform: show ? 'translateY(0)' : 'translateY(-300px)',
      }}
    >
      <span style={{ color: 'white' }}>Worth</span>
      <span style={{ color: 'black', WebkitTextStroke: '1px white' }}>It</span>
    </div>
  );
}

// ... rest of your App logic (unchanged) ...
export default function App() {
  const [foo, setFoo] = useState(0);
  const [userPrice, setUserPrice] = useState('');
  const priceInputRef = useRef(null);
  const inputSectionRef = useRef(null);
  const [showLogo, setShowLogo] = useState(false);
  const [splashVisible, setSplashVisible] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [filteredSuggestions, setFilteredSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);


  const [showMore, setShowMore] = useState(false);

  const [rows, setRows] = useState([]);
  const [worthinessScore, setWorthinessScore] = useState(0);
  const esRef = useRef(null);
  const [priceError, setPriceError] = useState('');
  const [showMoreButton, setShowMoreButton] = useState(false);

  const normalizeResult = (site, result) => {
    const title = result?.title || result?.name || result?.productTitle || '';
    let priceRaw =
      result?.price_text ||
      result?.priceText ||
      result?.price ||
      result?.amount ||
      result?.offer_price ||
      '';

    // Remove commas, ₹ symbol, spaces
    if (typeof priceRaw === 'string') {
      priceRaw = priceRaw.replace(/[,₹\s]/g, '');
    }

    let price = 0;
    if (!isNaN(priceRaw) && priceRaw !== '') {
      price = Number(priceRaw);
      // Round to 2 decimals
      price = Math.round(price * 100) / 100;
    }

    const url = result?.url || result?.link || result?.productUrl || '#';

    if (!title || !price) return null;

    return { site, title, price, url };
  };


  const upsertRow = (entry) => {
    setRows((prev) => {
      const others = prev.filter((r) => r.site !== entry.site);
      return [...others, entry];
    });
  };

  // UPDATED: polling version of fetchMore with fade-in spinner
  const fetchMore = async (q) => {
    const trimmedQuery = q?.trim();
    if (!trimmedQuery) return;

    setLoadingMore(true);
    setShowMoreButton(true);

    const poll = async () => {
      try {
        // Remove commas from userPrice before sending
        const price = userPrice?.replace(/,/g, '').trim();

        const url = `${API_BASE}/more?query=${encodeURIComponent(trimmedQuery)}${
          price ? `&user_price=${encodeURIComponent(price)}` : ''
        }`;

        const res = await fetch(url);
        if (!res.ok) throw new Error('Network response was not ok');

        const data = await res.json();

        if (data?.status === 'loading') {
          setTimeout(poll, 1500);
          return;
        }

        const results = data?.results || data || {};
        setRows(prev => {
          const newRows = Object.entries(results)
            .map(([site, result]) => normalizeResult(site, result))
            .filter(Boolean);

          const bySite = new Map(prev.map(r => [r.site, r]));
          newRows.forEach(e => bySite.set(e.site, e));
          return Array.from(bySite.values());
        });

        if (data?.worthit?.score !== undefined) {
          setWorthinessScore(data.worthit.score);
        }

        setLoadingMore(false);
        setShowMoreButton(false);
      } catch (err) {
        console.error("Error fetching more results:", err);
        setLoadingMore(false);
        setShowMoreButton(true);
      }
    };

    poll();
  };

  const startSearch = () => {
    const q = inputValue?.trim();
    // Remove commas before sending to backend
    const price = userPrice?.replace(/,/g, '').trim();

    // Add validation for the product query and price
    if (!q) {
      setPriceError("Please enter a product name.");
      return;
    }

    if (!price) {
      setPriceError("Please enter the price you paid.");
      return;
    }

    setPriceError(""); // Clear previous errors

    // Trigger the overlay orchestration
    setSplashVisible(true);

    if (esRef.current) {
      try { esRef.current.close(); } catch {}
      esRef.current = null;
    }

    const es = new EventSource(
      `${API_BASE}/compare?query=${encodeURIComponent(q)}&user_price=${encodeURIComponent(price)}`
    );
    esRef.current = es;

    es.onopen = () => {
      setRows([]);
      setShowMoreButton(false);
    };

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);

        if (payload.site === "_done_") {
          es.close();
          esRef.current = null;
          setShowMoreButton(true);

          if (payload?.worthit?.score !== undefined) {
            setWorthinessScore(payload.worthit.score);
          }

          setTimeout(() => {
            const tableElement = document.getElementById("results-table");
            if (tableElement) tableElement.scrollIntoView({ behavior: "smooth" });
          }, 200);

          return;
        }

        const entry = normalizeResult(payload.site, payload.result);

        // only add the row if the entry is not null
        if (entry) {
          upsertRow(entry);
        }

        if (payload?.worthit?.score !== undefined) {
          setWorthinessScore(payload.worthit.score);
        }

      } catch (err) {
        console.error("Error parsing SSE message:", err);
      }
    };

    es.onerror = () => {
      try { es.close(); } catch {}
      esRef.current = null;
    };
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);

    if (value.length > 0) {
      const filtered = productSuggestions.filter((s) =>
        s.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInputValue(suggestion);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('input')) setShowSuggestions(false);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (inputSectionRef.current?.scrollIntoView) {
        inputSectionRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setShowLogo(entry.isIntersecting),
      { threshold: 0.1 }
    );
    if (inputSectionRef.current) observer.observe(inputSectionRef.current);

    return () => observer.disconnect();
  }, []);
  const getWorthinessMessage = (score) => {
    if (score > 95) return "Great deal. You can go for it";
    if (score > 90) return "Good deal. See if you can negotiate";
    if (score > 80) return "Decent deal, other alternatives available online";
    if (score > 70) return "Average deal. Better prices available";
    if (score > 50) return "Below average. Consider comparing prices";
    if (score > 30) return "Poor deal. Many better options exist";
    return "Very poor deal. Avoid purchasing";
  };

  // Determine whether overlay should reveal: rows loaded OR polling/SSE finished (showMoreButton true & not loading)
  const rowsLoadedForOverlay = rows.length > 0 || (showMoreButton && !loadingMore);

 return (
  <div style={{ width: '100%', color: 'white', overflowX: 'hidden', position: 'relative' }}>
    <SplashOverlay
  visible={splashVisible}
  rowsLoaded={rowsLoadedForOverlay}
  onHide={() => setSplashVisible(false)}
/>


    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      <DarkVeil resolutionScale={window.devicePixelRatio} />
      <StarField />
    </div>

    <div style={{ position: 'relative', zIndex: 1 }}>
      <div style={{ minHeight: '100vh', position: 'relative' }}>
        {/* WorthIt section */}
        <div
          style={{
            position: 'absolute',
            top: '35%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: 'clamp(3rem, 10vw, 8rem)',
            fontWeight: 900,
            fontStyle: 'italic',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            zIndex: 10,
            animation: 'slideInLeft 2s forwards',
          }}
        >
          <span style={{ color: 'white' }}>Worth</span>
          <span style={{ color: 'black', WebkitTextStroke: '1px white' }}>It</span>
        </div>

        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '21%',
            transform: 'translate(-50%, -50%)',
            fontSize: '1.5rem',
            color: 'white',
            fontStyle: 'italic',
            whiteSpace: 'nowrap',
            zIndex: 10,
            opacity: 0,
            animation: 'slideInRightFade 1s forwards 1s',
          }}
        >
          Check if the price you’re paying is worth it
        </div>

        <style>{`
          @keyframes slideInRightFade { 0% { transform: translateX(100%) translateY(-50%); opacity: 0; } 100% { transform: translateX(0) translateY(-50%); opacity: 1; } }
        `}</style>

        {/* Logos */}
        <div
          style={{
            position: 'absolute',
            top: '55%',
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            gap: '3rem',
            opacity: 0,
            animation: 'fadeInUp 1.5s forwards 2s',
            zIndex: 10,
          }}
        >
          <img src={amazonLogo} alt="Amazon" style={{ height: '40px', marginTop: '25px' }} />
          <img src={flipkartLogo} alt="Flipkart" style={{ height: '99px', marginTop: '-16px' }} />
          <img src={cromaLogo} alt="Croma" style={{ height: '100px', marginTop: '-16px' }} />
          <img src={relianceLogo} alt="Reliance" style={{ height: '50px', marginTop: '3px' }} />
        </div>

        <div
          style={{
            position: 'absolute',
            top: '64%',
            left: '70%',
            transform: 'translateX(-50%)',
            color: 'white',
            fontStyle: 'italic',
            fontSize: '1rem',
            opacity: 0,
            animation: 'fadeInUp 1.5s forwards 2.5s',
            zIndex: 10,
          }}
        >
          (& many more....)
        </div>

        <style>{`
          @keyframes slideInLeft { 0% { left: -100%; } 100% { left: 50%; transform: translate(-50%, -50%); } }
          @keyframes slideInRightFade { 0% { right: -100%; opacity: 0; } 100% { right: 50%; transform: translate(50%, -50%); opacity: 1; } }
          @keyframes fadeInUp { 0% { transform: translateX(-50%) translateY(50px); opacity: 0; } 100% { transform: translateX(-50%) translateY(0); opacity: 1; } }
          @keyframes splashAnim { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(10); opacity: 1; } 100% { transform: scale(10); opacity: 0; } }

          /* Table row reveal animation */
          @keyframes rowReveal {
            0% { opacity: 0; transform: translateY(8px); }
            100% { opacity: 1; transform: translateY(0); }
          }
          .table-row-anim {
            opacity: 0;
            transform: translateY(8px);
            animation-name: rowReveal;
            animation-duration: 420ms;
            animation-fill-mode: forwards;
            animation-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
          }
        `}</style>
      </div>

      {/* Input Section */}
      <div
        ref={inputSectionRef}
        style={{
          minHeight: '90vh',
          paddingTop: '6rem',
          position: 'relative',
          zIndex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            transform: rows.length > 0 ? 'translateY(-150px)' : 'translateY(0)',
            transition: 'transform 0.8s ease-in-out',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <InputLogo show={showLogo} />

          <div
            style={{
              width: '100%',
              minHeight: '80vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              padding: '2rem',
              transition: 'opacity 1s ease-in-out',
            }}
          >
            <h2
              style={{
                fontSize: '1.25rem',
                marginBottom: '1rem',
                fontWeight: 900,
                fontStyle: 'italic',
                color: 'white',
              }}
            >
              What product do you want to search for?
            </h2>

            <div style={{ position: 'relative' }}>
              <input
                placeholder="Type product name"
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setShowSuggestions(false);
                    if (priceInputRef.current) priceInputRef.current.focus();
                  } else if (e.key === 'Escape') {
                    setShowSuggestions(false);
                  }
                }}
                spellCheck="false"
                style={{
                  padding: '1rem',
                  fontSize: '1.1rem',
                  width: '500px',
                  borderRadius: '100px',
                  border: '3px solid white',
                  backgroundColor: 'black',
                  color: 'white',
                  outline: 'none',
                  fontStyle: 'italic',
                  fontFamily: "'Poppins', sans-serif",
                }}
              />

              {showSuggestions && filteredSuggestions.length > 0 && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    width: '100%',
                    backgroundColor: 'black',
                    border: '1px solid white',
                    borderRadius: '8px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    zIndex: 10,
                  }}
                >
                  {filteredSuggestions.map((s, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSuggestionClick(s)}
                      onMouseDown={(e) => e.preventDefault()}
                      style={{ padding: '0.5rem 1rem', cursor: 'pointer', color: 'white' }}
                    >
                      {s}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <input
              ref={priceInputRef}
              type="text" 
              // changed from number to text to allow commas
              placeholder="Enter product price"
              value={userPrice}
              onChange={(e) => {
                const input = e.target;
                // Raw value user currently has in the input (may include commas)
                const raw = input.value || '';

                // Calculate cursor position and digits before cursor
                const selectionStart = input.selectionStart ?? raw.length;
                const digitsBeforeCursor = raw.slice(0, selectionStart).replace(/\D/g, '').length;

                // Extract only digits from the entire input
                const digits = raw.replace(/\D/g, '');

                // Format digits with Indian grouping
                const formatted = digits ? Number(digits).toLocaleString('en-IN') : '';

                // Compute the new cursor position in formatted string corresponding to digitsBeforeCursor
                let newCursorPos = 0;
                if (digitsBeforeCursor === 0) {
                  newCursorPos = 0;
                } else {
                  let digitCount = 0;
                  let found = false;
                  for (let i = 0; i < formatted.length; i++) {
                    if (/\d/.test(formatted[i])) digitCount++;
                    if (digitCount === digitsBeforeCursor) {
                      newCursorPos = i + 1;
                      found = true;
                      break;
                    }
                  }
                  if (!found) {
                    // Fallback to end
                    newCursorPos = formatted.length;
                  }
                }

                // Update state
                setUserPrice(formatted);

                // Restore cursor after state update/render
                const el = input;
                setTimeout(() => {
                  try {
                    el.setSelectionRange(newCursorPos, newCursorPos);
                  } catch (err) {
                    // ignore if it fails (safe fallback)
                  }
                }, 0);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') startSearch();
                else if (e.key === 'Escape') setShowSuggestions(false);
              }}
              style={{
                marginTop: '1rem',
                width: '500px',
                height: '65px',
                backgroundColor: 'black',
                border: '3px solid white',
                borderRadius: '50px',
                color: 'white',
                fontSize: '1.1rem',
                padding: '0 1rem',
                outline: 'none',
                WebkitAppearance: 'none',
                MozAppearance: 'textfield',
                fontFamily: "'Poppins', sans-serif",
                fontStyle: 'italic',

              }}
            />

            {priceError && (
              <div style={{ color: 'red', marginTop: '0.5rem', fontStyle: 'italic' }}>
                {priceError}
              </div>
            )}

            <div style={{ marginTop: '1.5rem' }}>
              <SearchButton onClick={startSearch} />
            </div>
          </div>
        </div>

        {/* Linear Progress */}
        <div style={{ width: '90%', maxWidth: '900px', margin: '2rem auto', textAlign: 'center' }}>
          {worthinessScore > 0 && (
            <div style={{ marginBottom: '0.1rem', fontWeight: 'bold', fontStyle: 'italic' }}>
              {getWorthinessMessage(worthinessScore)}
            </div>
          )}

          <LinearProgressBar score={worthinessScore} />
        </div>

        {/* Results */}
        {rows.length > 0 && (
          <div style={{ width: '90%', maxWidth: '900px', margin: '1rem auto' }}>
            <table
              id="results-table"
              style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #444', tableLayout: 'fixed' }}
            >
              <colgroup>
                <col style={{ width: '18%' }} />
                <col style={{ width: '54%' }} />
                <col style={{ width: '18%' }} />
                <col style={{ width: '10%' }} />
              </colgroup>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'left' }}>Site</th>
                  <th style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'center' }}>Title</th>
                  <th
                    style={{
                      borderBottom: '1px solid #444',
                      padding: '8px 20px 8px 8px', // top/right/bottom/left — more right padding
                      textAlign: 'center',
                      verticalAlign: 'middle',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    Price
                  </th>
                  <th style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'center' }}>Link</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={idx}
                    className="table-row-anim"
                    style={{
                      // Stagger a little for nicer reveal (first batch will be quick)
                      animationDelay: `${Math.min(idx, 8) * 60}ms`,
                    }}
                  >
                    <td style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'left', overflowWrap: 'anywhere' }}>{row.site}</td>
                    <td style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'left', overflowWrap: 'break-word' }}>{row.title}</td>
                    <td
                      style={{
                        borderBottom: '1px solid #444',
                        padding: '8px 20px 8px 8px', // same paddingRight as header
                        textAlign: 'right',
                        whiteSpace: 'nowrap',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      ₹{row.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    <td style={{ borderBottom: '1px solid #444', padding: '8px', textAlign: 'center' }}>
                      <a href={row.url} target="_blank" rel="noopener noreferrer">View</a>
                    </td>
                  </tr>
                ))}
              </tbody>

            </table>
          </div>
        )}

        {/* Show More / Spinner */}
        {showMoreButton && (
          <div style={{ margin: '2rem', textAlign: 'center', height: '80px', transition: 'opacity 0.4s ease' }}>
            {loadingMore ? (
              <div style={{ position: 'relative', width: '60px', height: '60px', margin: '0 auto', animation: 'fadeIn 0.4s ease' }}>
                {[...Array(8)].map((_, i) => {
                  const angle = (i * 45) * (Math.PI / 180); // 8 dots evenly spaced
                  const radius = 20;
                  return (
                    <div
                      key={i}
                      style={{
                        width: '10px',
                        height: '10px',
                        backgroundColor: 'white',
                        borderRadius: '50%',
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        margin: '-5px',
                        transform: `translate(${radius * Math.cos(angle)}px, ${radius * Math.sin(angle)}px)`,
                        animation: `orbit 1.2s linear infinite`,
                        animationDelay: `${i * 0.15}s`,
                      }}
                    />
                  );
                })}
                <style>{`
                  @keyframes orbit {
                    0% { transform: rotate(0deg) translate(20px) rotate(0deg); }
                    100% { transform: rotate(360deg) translate(20px) rotate(-360deg); }
                  }
                  @keyframes fadeIn {
                    from { opacity: 0 }
                    to { opacity: 1 }
                  }
                `}</style>
              </div>
            ) : (
              <button
                onClick={() => fetchMore(inputValue)}
                style={{
                  padding: '1rem 2rem',
                  borderRadius: '12px',
                  backgroundColor: 'white',
                  color: 'black',
                  fontWeight: 'bold',
                  transition: 'opacity 0.4s ease',
                }}
              >
                Show More
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  </div>
 );
}
