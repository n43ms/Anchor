/**
 * 3D Silk Threads & Glowing Checkpoint Pointers
 * Full-screen background Canvas mounted at z-index: -1.
 * Simulates undulating silk threads in wind using CatmullRom splines,
 * metallic physical gold material, glowing diamond checkpoints,
 * and floating operator data labels.
 */
"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

interface ThreadData {
  id: string;
  label: string;
  checkpointLabel: string;
  points: THREE.Vector3[];
  speed: number;
  phase: number;
  color: number;
  radius: number;
}

// Generates initial control points for flowing 3D splines
function generateThreadCurves(): ThreadData[] {
  return [
    {
      id: "thread-gamma-1",
      label: "THREAD gamma-1",
      checkpointLabel: "CHECKPOINT c1-5",
      points: [
        new THREE.Vector3(-14, 5, -8),
        new THREE.Vector3(-8, 3, -4),
        new THREE.Vector3(-2, 0, -2),
        new THREE.Vector3(4, -2, -5),
        new THREE.Vector3(10, 1, -7),
        new THREE.Vector3(16, -4, -10),
      ],
      speed: 0.7,
      phase: 0,
      color: 0xffd700, // Metallic Gold
      radius: 0.045,
    },
    {
      id: "thread-alpha-2",
      label: "THREAD alpha-2",
      checkpointLabel: "CHECKPOINT c2-12",
      points: [
        new THREE.Vector3(-15, -4, -10),
        new THREE.Vector3(-9, -1, -6),
        new THREE.Vector3(-3, 2, -3),
        new THREE.Vector3(3, 4, -4),
        new THREE.Vector3(9, -1, -6),
        new THREE.Vector3(15, 3, -9),
      ],
      speed: 0.5,
      phase: 2.1,
      color: 0xf6c453, // Strand Gold
      radius: 0.038,
    },
    {
      id: "thread-zeta-9",
      label: "THREAD zeta-9",
      checkpointLabel: "CHECKPOINT c3-8",
      points: [
        new THREE.Vector3(-12, 7, -12),
        new THREE.Vector3(-6, -3, -7),
        new THREE.Vector3(1, -4, -3),
        new THREE.Vector3(7, 2, -5),
        new THREE.Vector3(13, -2, -8),
      ],
      speed: 0.6,
      phase: 4.3,
      color: 0xe6b800,
      radius: 0.035,
    },
  ];
}

function SilkThread({ thread, index }: { thread: ThreadData; index: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const diamondRef = useRef<THREE.Mesh>(null);

  const basePoints = useMemo(() => thread.points.map((p) => p.clone()), [thread.points]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime() * thread.speed + thread.phase;

    // Mutate spline control points to simulate silk undulating gently in the breeze
    const animatedPoints = basePoints.map((pt, i) => {
      const offsetFactor = Math.sin(t + i * 0.9) * 0.7;
      const verticalFactor = Math.cos(t * 0.8 + i * 0.6) * 0.5;
      const depthFactor = Math.sin(t * 0.6 + i * 1.1) * 0.4;
      return new THREE.Vector3(
        pt.x + offsetFactor * 0.4,
        pt.y + verticalFactor,
        pt.z + depthFactor
      );
    });

    const curve = new THREE.CatmullRomCurve3(animatedPoints, false, "catmullrom", 0.5);
    const newGeometry = new THREE.TubeGeometry(curve, 120, thread.radius, 12, false);

    if (meshRef.current) {
      meshRef.current.geometry.dispose();
      meshRef.current.geometry = newGeometry;
    }

    // Position glowing diamond checkpoint at specific point along curve
    const checkpointT = ((Math.sin(t * 0.25 + index) + 1) / 2) * 0.6 + 0.2;
    const ptOnCurve = curve.getPoint(checkpointT);
    if (diamondRef.current) {
      diamondRef.current.position.copy(ptOnCurve);
      diamondRef.current.rotation.x += 0.015;
      diamondRef.current.rotation.y += 0.02;
    }
  });

  return (
    <group>
      {/* Undulating Gold Silk Tube */}
      <mesh ref={meshRef}>
        <tubeGeometry args={[new THREE.CatmullRomCurve3(basePoints), 120, thread.radius, 12, false]} />
        <meshPhysicalMaterial
          color={thread.color}
          metalness={0.85}
          roughness={0.18}
          clearcoat={0.9}
          clearcoatRoughness={0.1}
          reflectivity={0.9}
          emissive={0x554000}
          emissiveIntensity={0.25}
        />
      </mesh>

      {/* Glowing Diamond Checkpoint */}
      <mesh ref={diamondRef}>
        <icosahedronGeometry args={[0.18, 0]} />
        <meshStandardMaterial
          color={0xffffff}
          emissive={thread.color}
          emissiveIntensity={2.5}
          roughness={0.1}
          metalness={0.9}
        />

        {/* Floating Data Pointer Tag */}
        <Html
          position={[0.4, 0.4, 0]}
          distanceFactor={12}
          center
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          <div className="flex items-center gap-1.5 whitespace-nowrap rounded-sm border border-white/20 bg-black/70 px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest text-white shadow-xl backdrop-blur-md">
            <span className="h-1.5 w-1.5 animate-ping rounded-full bg-strand-gold" />
            <span>{thread.label}</span>
            <span className="text-zinc-500">|</span>
            <span className="text-strand-gold">{thread.checkpointLabel}</span>
          </div>
        </Html>
      </mesh>
    </group>
  );
}

function Scene() {
  const threads = useMemo(() => generateThreadCurves(), []);

  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 15, 10]} intensity={1.5} color={0xfff6d6} />
      <pointLight position={[-10, -5, -5]} intensity={0.8} color={0xffd700} />
      <pointLight position={[0, 10, 5]} intensity={1.2} color={0xffea80} />

      {threads.map((thread, idx) => (
        <SilkThread key={thread.id} thread={thread} index={idx} />
      ))}
    </>
  );
}

export function GoldenThreadsCanvas() {
  const [mounted, setMounted] = useState(false);
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    setMounted(true);
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) setHasWebGL(false);
    } catch {
      setHasWebGL(false);
    }
  }, []);

  if (!mounted || !hasWebGL) {
    // Fallback if running in headless test or unsupported WebGL
    return (
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-surface-page cyber-bg opacity-70"
      />
    );
  }

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 h-full w-full overflow-hidden bg-surface-page"
    >
      <Canvas
        camera={{ position: [0, 0, 9], fov: 50 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        dpr={[1, 2]}
      >
        <Scene />
      </Canvas>
      {/* Subtle bottom vignette to ensure terminal & controls readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-surface-page via-transparent to-surface-page/30" />
    </div>
  );
}
