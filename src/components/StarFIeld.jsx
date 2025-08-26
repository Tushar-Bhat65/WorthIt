import { useState, useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

// This component holds the logic for the stars
function StarPoints() {
  const ref = useRef();

  // The number of stars
  const count = 5000;
  
  // The radius of the sphere in which stars are generated
  const sphereRadius = 80;

  // useMemo will only recompute the values when the dependencies change (which they won't)
  const [positions, speeds] = useMemo(() => {
    // Generate random star positions inside a sphere
    const pos = new Float32Array(count * 3);
    const spd = new Float32Array(count);
    
    const randomInSphere = (r) => {
      // This generates a random point uniformly inside a sphere
      // See: https://mathworld.wolfram.com/SpherePointPicking.html
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);
      return [x, y, z];
    }
    
    for (let i = 0; i < count; i++) {
        const [x, y, z] = randomInSphere(sphereRadius);
        pos[i * 3] = x;
        pos[i * 3 + 1] = y;
        pos[i * 3 + 2] = z;
        
        // Give each star a random speed
        spd[i] = 0.5 + Math.random() * 2;
    }
    
    return [pos, spd];
  }, [count, sphereRadius]);

  // useFrame is a hook that runs on every rendered frame
  useFrame((state, delta) => {
    const positions = ref.current.geometry.attributes.position.array;
    
    // Animate each star
    for (let i = 0; i < count; i++) {
      // The current z position (index is i * 3 + 2)
      let z = positions[i * 3 + 2];
      
      // Move the star towards the camera
      z += delta * speeds[i];
      
      // If the star has passed the camera, respawn it at the back
      if (z > sphereRadius / 2) {
        // Reset to a position far behind the camera
        const [nx, ny, nz] = randomInSphere(sphereRadius);
        positions[i * 3] = nx;
        positions[i * 3 + 1] = ny;
        positions[i * 3 + 2] = -nz; // Start from the back
      } else {
        positions[i * 3 + 2] = z;
      }
    }
    
    // This tells three.js to update the positions in the GPU
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    // <Points> is an efficient way to render a large number of particles
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        color="#ffffff"
        size={0.015}
        sizeAttenuation={true} // Makes points smaller the further they are
        depthWrite={false}     // Prevents transparent points from occluding each other weirdly
      />
    </Points>
  );
}

// The main export component
export default function StarField() {
  return (
    <div style={{ 
        position: 'fixed', 
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%', 
        background: 'black',
        pointerEvents: 'none',
        zIndex: -1 // Place it behind other content
    }}>
      {/* Canvas is the main scene container from react-three-fiber */}
      <Canvas camera={{ position: [0, 0, 1], fov: 75 }}>
        <StarPoints />
      </Canvas>
    </div>
  );
}