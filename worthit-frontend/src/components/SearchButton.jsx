// src/components/SearchButton.jsx
import React from "react";
import "./SearchButton.css";

export default function SearchButton({ onClick, disabled, label }) {
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();

    console.log("[SearchButton] click received");
    try {
      if (typeof onClick === "function") {
        onClick();
      } else {
        console.warn("[SearchButton] onClick prop is not a function:", onClick);
      }
    } catch (err) {
      console.error("[SearchButton] onClick threw:", err);
    }
  };

  return (
    <button
      type="button"
      className="button"
      onClick={handleClick}
      disabled={disabled}
      aria-label={label || "Search"}
      title={label || "Search"}
    >
      {label || "Search"} {/* <-- renders the label if provided, else defaults to "Search" */}
    </button>
  );
}
