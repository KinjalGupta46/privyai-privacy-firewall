import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * FirewallShield3D
 * Minimal, high-aesthetic 3D geometric privacy core powered by Three.js.
 * Reacts dynamically to firewall status:
 * - 'ALLOW' / 'IDLE' : Emerald & Cyan (Safe state)
 * - 'REDACT'         : Amber & Cyber Gold (Sanitizing)
 * - 'BLOCK'          : Crimson Alert Pulse (Threat deflected)
 */
export default function FirewallShield3D({ status = 'IDLE', riskScore = 0.0, isScanning = false }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 240;
    const height = container.clientHeight || 200;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 4.2;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Color definitions
    const colors = {
      IDLE: { core: 0x06b6d4, wire: 0x10b981, glow: 0x0891b2 },
      ALLOW: { core: 0x10b981, wire: 0x34d399, glow: 0x059669 },
      REDACT: { core: 0xf59e0b, wire: 0xfbbf24, glow: 0xd97706 },
      BLOCK: { core: 0xef4444, wire: 0xf87171, glow: 0xdc2626 },
    };

    const currentPalette = colors[status] || colors.IDLE;

    // Outer Dual Rings
    const ringGeo1 = new THREE.TorusGeometry(1.65, 0.015, 16, 100);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: currentPalette.wire,
      transparent: true,
      opacity: 0.5,
    });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
    scene.add(ring1);

    const ringGeo2 = new THREE.TorusGeometry(1.4, 0.012, 16, 100);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: currentPalette.glow,
      transparent: true,
      opacity: 0.35,
    });
    const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
    ring2.rotation.x = Math.PI / 3;
    scene.add(ring2);

    // Main 3D Shield Core (Icosahedron Wireframe + Translucent Inner Facets)
    const icosaGeo = new THREE.IcosahedronGeometry(0.95, 1);
    
    // Wireframe overlay
    const wireMat = new THREE.MeshBasicMaterial({
      color: currentPalette.wire,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
    });
    const icosaWire = new THREE.Mesh(icosaGeo, wireMat);
    scene.add(icosaWire);

    // Inner Crystal Core
    const innerGeo = new THREE.OctahedronGeometry(0.55, 0);
    const innerMat = new THREE.MeshStandardMaterial({
      color: currentPalette.core,
      metalness: 0.8,
      roughness: 0.2,
      emissive: currentPalette.core,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.85,
    });
    const innerCore = new THREE.Mesh(innerGeo, innerMat);
    scene.add(innerCore);

    // Ambient & Point Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(currentPalette.core, 2.5, 10);
    pointLight.position.set(2, 2, 3);
    scene.add(pointLight);

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width - 0.5) * 0.8;
      mouseY = ((e.clientY - rect.top) / height - 0.5) * 0.8;
    };
    container.addEventListener('mousemove', handleMouseMove);

    // Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();
      const speedMultiplier = isScanning ? 3.5 : 1.0;

      // Rotations
      ring1.rotation.z += 0.005 * speedMultiplier;
      ring1.rotation.x = Math.sin(elapsedTime * 0.5) * 0.3;

      ring2.rotation.y += 0.008 * speedMultiplier;
      ring2.rotation.z += 0.003 * speedMultiplier;

      icosaWire.rotation.x += 0.007 * speedMultiplier;
      icosaWire.rotation.y += 0.01 * speedMultiplier;

      innerCore.rotation.x -= 0.012 * speedMultiplier;
      innerCore.rotation.y -= 0.009 * speedMultiplier;

      // Subtle breath pulse
      const pulse = 1 + Math.sin(elapsedTime * 2.5) * 0.04;
      icosaWire.scale.set(pulse, pulse, pulse);

      // Smooth camera tilt towards mouse
      camera.position.x += (mouseX - camera.position.x) * 0.05;
      camera.position.y += (-mouseY - camera.position.y) * 0.05;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };

    animate();

    // Resize handling
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      renderer.dispose();
      ringGeo1.dispose();
      ringGeo2.dispose();
      icosaGeo.dispose();
      innerGeo.dispose();
      ringMat1.dispose();
      ringMat2.dispose();
      wireMat.dispose();
      innerMat.dispose();
    };
  }, [status, isScanning]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '100%',
          cursor: 'grab',
          position: 'relative',
        }}
      />
      {/* Status Overlay Badge */}
      <div
        style={{
          position: 'absolute',
          bottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 12px',
          borderRadius: '20px',
          fontSize: '11px',
          fontWeight: '600',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          backdropFilter: 'blur(8px)',
          background:
            status === 'BLOCK'
              ? 'rgba(239, 68, 68, 0.16)'
              : status === 'REDACT'
              ? 'rgba(245, 158, 11, 0.16)'
              : 'rgba(16, 185, 129, 0.16)',
          border: `1px solid ${
            status === 'BLOCK'
              ? 'var(--color-block-border)'
              : status === 'REDACT'
              ? 'var(--color-redact-border)'
              : 'var(--color-allow-border)'
          }`,
          color:
            status === 'BLOCK'
              ? 'var(--color-block)'
              : status === 'REDACT'
              ? 'var(--color-redact)'
              : 'var(--color-allow)',
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: 'currentColor',
            boxShadow: '0 0 8px currentColor',
            animation: isScanning ? 'pulseSubtle 0.5s infinite alternate' : 'none',
          }}
        />
        {isScanning ? 'Interception Active' : `Firewall: ${status}`}
      </div>
    </div>
  );
}
