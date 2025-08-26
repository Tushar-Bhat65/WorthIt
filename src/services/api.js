// src/services/api.js

const BASE_URL = "http://localhost:8000"; // Change to your backend URL when deployed

// Fetch initial results (Amazon, Flipkart, Croma)
export async function fetchCompareResults(productName, maxPrice) {
  try {
    const response = await fetch(
      `${BASE_URL}/compare?query=${encodeURIComponent(productName)}&max_price=${encodeURIComponent(maxPrice)}`
    );
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching compare results:", error);
    return { error: error.message };
  }
}

// Fetch more results (Reliance, Poorvika, Pai, Sangeetha)
export async function fetchMoreResults(productName, maxPrice) {
  try {
    const response = await fetch(
      `${BASE_URL}/more?query=${encodeURIComponent(productName)}&max_price=${encodeURIComponent(maxPrice)}`
    );
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching more results:", error);
    return { error: error.message };
  }
}
