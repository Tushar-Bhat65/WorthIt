// src/components/ProductInput.jsx
import { useRef, useEffect, useState } from 'react';

export default function ProductInput() {
  const inputRef = useRef(null);
  const [product, setProduct] = useState('');

  // fade-in animation
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 500); // fade in after scroll
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      ref={inputRef}
      style={{
        width: '100%',
        minHeight: '100vh',
        background: 'black',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: visible ? 1 : 0,
        transition: 'opacity 1s ease-in-out',
        color: 'white',
        padding: '2rem',
      }}
    >
      <h2 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Search Product</h2>
      <input
        type="text"
        placeholder="Type product name..."
        value={product}
        onChange={(e) => setProduct(e.target.value)}
        style={{
          padding: '1rem',
          fontSize: '1.2rem',
          width: '300px',
          borderRadius: '8px',
          border: 'none',
          outline: 'none',
        }}
      />
      <div
        style={{
          marginTop: '2rem',
          width: '300px',
          height: '50px',
          background: '#111',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Placeholder for product price/results */}
        Product Price / Results Here
      </div>
    </div>
  );
}
