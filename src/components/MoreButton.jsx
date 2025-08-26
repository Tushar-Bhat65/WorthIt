import React from 'react';
import './MoreButton.css'; // make sure your CSS is the full cyber-toggle CSS you pasted

export default function MoreButton({ onClick }) {
  return (
    <div className="cyber-toggle" onClick={onClick} style={{ cursor: 'pointer' }}>
      <input id="toggle" className="cyber-input" type="checkbox" />
      <label htmlFor="toggle" className="cyber-label">
        <div className="cyber-core">
          <div className="cyber-toggle-circle"></div>
        </div>
        <div className="cyber-power-line"></div>
        <div className="cyber-power-ring">
          <div
            style={{ '--x': '10%', '--y': '20%', '--px': '15px', '--py': '-10px', '--delay': '0.1s' }}
            className="ring-particle"
          ></div>
          <div
            style={{ '--x': '70%', '--y': '30%', '--px': '-10px', '--py': '15px', '--delay': '0.3s' }}
            className="ring-particle"
          ></div>
          <div
            style={{ '--x': '40%', '--y': '80%', '--px': '20px', '--py': '10px', '--delay': '0.5s' }}
            className="ring-particle"
          ></div>
          <div
            style={{ '--x': '90%', '--y': '60%', '--px': '-15px', '--py': '-15px', '--delay': '0.7s' }}
            className="ring-particle"
          ></div>
        </div>
        <div className="cyber-particles">
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
        </div>
      </label>
    </div>
  );
}
