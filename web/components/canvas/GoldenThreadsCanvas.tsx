/**
 * 3D Golden Silk Threads & In-Sync Agent Steps Centerpiece
 *
 * Implements:
 * 1. Dense bundle of 64 continuous vector paths (high-resolution line strips)
 * 2. Base trajectory: Gentle macroscopic horizontal dip
 * 3. Volumetric 3D Pinching: Tightly focused at viewport center, spreading at edges
 * 4. Constant traveling wave motion driven by time uniform (x - speed * t)
 * 5. Unique phase & radial offset per strand creating interwoven 3D twisting ribbon
 * 6. Additive blending creating a luminous hot-white core at overlaps
 * 7. Edge alpha fading to complete transparency at canvas boundaries
 * 8. Agent Step Diamonds mathematically anchored ON the main golden strand
 */
"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

const STRAND_COUNT = 64;
const POINTS_PER_STRAND = 80;
const X_MIN = -16;
const X_MAX = 16;
const SPEED = 1.15;

// Macroscopic base trajectory
function baseTrajectory(x: number): number {
  return -0.45 * Math.cos((x / 16) * (Math.PI / 2)) - 0.2;
}

// 3D volumetric bundling / pinch factor: tight at center, spreading at edges
function pinchFactor(x: number): number {
  const normX = x / 16;
  return 0.24 + 0.76 * (normX * normX);
}

// Displacement function for a specific strand at (x, t)
function getStrandDisplacement(
  x: number,
  t: number,
  strandIndex: number,
  totalStrands: number
): { y: number; z: number } {
  const u = x - t * SPEED;
  const pinch = pinchFactor(x);

  if (strandIndex === 0) {
    // Primary Main Golden Strand (central brightest trajectory)
    const yDisp =
      pinch *
      (0.48 * Math.sin(0.42 * u) +
        0.24 * Math.sin(0.85 * u + 0.4) +
        0.12 * Math.cos(1.7 * u - 0.3));
    const zDisp = pinch * (0.35 * Math.cos(0.52 * u)) - 4.2;
    return { y: yDisp, z: zDisp };
  }

  // Secondary strands with unique radial and phase shifts
  const normalizedIndex = strandIndex / totalStrands;
  const phase = normalizedIndex * Math.PI * 2 * 3.5;
  const radialRadius = (normalizedIndex - 0.5) * 2.2;
  const twistAngle = normalizedIndex * Math.PI * 4 + 0.25 * t;

  const yDisp =
    pinch *
    (radialRadius * Math.cos(twistAngle + 0.16 * u) +
      0.45 * Math.sin(0.42 * u + phase) +
      0.22 * Math.sin(0.85 * u + 2 * phase) +
      0.12 * Math.cos(1.7 * u - phase));

  const zDisp =
    pinch *
      (radialRadius * Math.sin(twistAngle + 0.16 * u) +
        0.32 * Math.cos(0.52 * u + phase)) -
    4.2;

  return { y: yDisp, z: zDisp };
}

// Agent Step metadata anchored on the main strand
const AGENT_STEPS = [
  {
    id: "step-1",
    label: "STEP 1: LEASE ACQUIRED",
    subLabel: "worker-1 held",
    x: -9.5,
  },
  {
    id: "step-2",
    label: "STEP 2: AST EXECUTION",
    subLabel: "step 14 durable",
    x: -3.2,
  },
  {
    id: "step-3",
    label: "STEP 3: FENCE VERIFIED",
    subLabel: "seq 4092 assigned",
    x: 3.2,
  },
  {
    id: "step-4",
    label: "STEP 4: CHECKPOINT SECURED",
    subLabel: "0 duplicate effects",
    x: 9.5,
  },
];

function StrandBundleMesh() {
  const lineMeshRef = useRef<THREE.LineSegments>(null);
  const mainTubeMeshRef = useRef<THREE.Mesh>(null);

  // Initialize position and color buffer arrays
  const { positions, colors, indices } = useMemo(() => {
    const totalVertices = STRAND_COUNT * POINTS_PER_STRAND;
    const posArr = new Float32Array(totalVertices * 3);
    const colArr = new Float32Array(totalVertices * 4); // RGBA
    const idxArr: number[] = [];

    let vertexOffset = 0;
    for (let s = 0; s < STRAND_COUNT; s++) {
      for (let p = 0; p < POINTS_PER_STRAND; p++) {
        const x = X_MIN + (p / (POINTS_PER_STRAND - 1)) * (X_MAX - X_MIN);
        posArr[vertexOffset * 3] = x;
        posArr[vertexOffset * 3 + 1] = 0;
        posArr[vertexOffset * 3 + 2] = -4;

        colArr[vertexOffset * 4] = 1.0;
        colArr[vertexOffset * 4 + 1] = 0.85;
        colArr[vertexOffset * 4 + 2] = 0.35;
        colArr[vertexOffset * 4 + 3] = 0.5;

        if (p < POINTS_PER_STRAND - 1) {
          idxArr.push(vertexOffset, vertexOffset + 1);
        }
        vertexOffset++;
      }
    }

    return {
      positions: posArr,
      colors: colArr,
      indices: new Uint16Array(idxArr),
    };
  }, []);

  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geom.setAttribute("color", new THREE.BufferAttribute(colors, 4));
    geom.setIndex(new THREE.BufferAttribute(indices, 1));
    return geom;
  }, [positions, colors, indices]);

  const lineMaterial = useMemo(() => {
    return new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      linewidth: 1,
    });
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (!lineMeshRef.current) return;

    const posAttr = lineMeshRef.current.geometry.attributes.position as THREE.BufferAttribute;
    const colAttr = lineMeshRef.current.geometry.attributes.color as THREE.BufferAttribute;
    const posData = posAttr.array as Float32Array;
    const colData = colAttr.array as Float32Array;

    const mainStrandPoints: THREE.Vector3[] = [];

    let vertexIdx = 0;
    for (let s = 0; s < STRAND_COUNT; s++) {
      const isMain = s === 0;
      const baseOpacity = isMain ? 0.95 : 0.2 + (s % 7) * 0.08;

      for (let p = 0; p < POINTS_PER_STRAND; p++) {
        const x = X_MIN + (p / (POINTS_PER_STRAND - 1)) * (X_MAX - X_MIN);
        const baseY = baseTrajectory(x);
        const { y: yDisp, z: zDisp } = getStrandDisplacement(x, t, s, STRAND_COUNT);

        const finalY = baseY + yDisp;
        const finalZ = zDisp;

        posData[vertexIdx * 3] = x;
        posData[vertexIdx * 3 + 1] = finalY;
        posData[vertexIdx * 3 + 2] = finalZ;

        if (isMain) {
          mainStrandPoints.push(new THREE.Vector3(x, finalY, finalZ));
        }

        // Edge alpha masking: smoothly fade to 0 at extreme left and right boundaries
        const normDist = Math.abs(x) / 16;
        const edgeAlpha = Math.max(0, 1 - normDist * normDist * normDist * normDist);
        const finalAlpha = baseOpacity * edgeAlpha;

        if (isMain) {
          // Hot incandescent golden-white core for main strand
          colData[vertexIdx * 4] = 1.0;
          colData[vertexIdx * 4 + 1] = 0.94;
          colData[vertexIdx * 4 + 2] = 0.72;
          colData[vertexIdx * 4 + 3] = finalAlpha;
        } else {
          // Vibrant gold/amber spectrum for surrounding strands
          const amberShift = (s % 5) * 0.04;
          colData[vertexIdx * 4] = 0.96;
          colData[vertexIdx * 4 + 1] = 0.76 - amberShift;
          colData[vertexIdx * 4 + 2] = 0.25 - amberShift * 0.5;
          colData[vertexIdx * 4 + 3] = finalAlpha;
        }

        vertexIdx++;
      }
    }

    posAttr.needsUpdate = true;
    colAttr.needsUpdate = true;

    // Update the physical 3D tube geometry for the Main Golden Strand
    if (mainTubeMeshRef.current && mainStrandPoints.length > 2) {
      const curve = new THREE.CatmullRomCurve3(mainStrandPoints, false, "catmullrom", 0.4);
      mainTubeMeshRef.current.geometry.dispose();
      mainTubeMeshRef.current.geometry = new THREE.TubeGeometry(curve, 90, 0.042, 8, false);
    }
  });

  return (
    <group>
      {/* 64-Strand Additively Blended Vector Bundle */}
      <lineSegments ref={lineMeshRef} geometry={geometry} material={lineMaterial} />

      {/* Main Golden Strand Radiant Tube Centerpiece */}
      <mesh ref={mainTubeMeshRef}>
        <tubeGeometry
          args={[
            new THREE.CatmullRomCurve3([
              new THREE.Vector3(-16, 0, -4.2),
              new THREE.Vector3(0, -0.6, -4.2),
              new THREE.Vector3(16, 0, -4.2),
            ]),
            90,
            0.042,
            8,
            false,
          ]}
        />
        <meshStandardMaterial
          color={0xffeedd}
          emissive={0xffc83b}
          emissiveIntensity={2.8}
          roughness={0.15}
          metalness={0.9}
        />
      </mesh>
    </group>
  );
}

function AnchoredAgentStepNode({ step }: { step: (typeof AGENT_STEPS)[0] }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (!meshRef.current) return;

    // Calculate exact mathematical coordinates ON the Main Golden Strand (strandIndex = 0)
    const baseY = baseTrajectory(step.x);
    const { y: yDisp, z: zDisp } = getStrandDisplacement(step.x, t, 0, STRAND_COUNT);

    meshRef.current.position.set(step.x, baseY + yDisp, zDisp);
    meshRef.current.rotation.x += 0.018;
    meshRef.current.rotation.y += 0.024;
  });

  return (
    <mesh ref={meshRef}>
      {/* Radiant Diamond Checkpoint */}
      <icosahedronGeometry args={[0.2, 0]} />
      <meshStandardMaterial
        color={0xffffff}
        emissive={0xffd700}
        emissiveIntensity={3.5}
        roughness={0.05}
        metalness={0.95}
      />

      {/* Floating Operator Data Label pinned directly above the node */}
      <Html
        position={[0.35, 0.4, 0]}
        distanceFactor={13}
        center
        style={{ pointerEvents: "none", userSelect: "none" }}
      >
        <div className="flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-strand-gold/40 bg-black/80 px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-white shadow-2xl backdrop-blur-xl">
          <span className="h-1.5 w-1.5 animate-ping rounded-full bg-strand-gold shadow-glow-gold" />
          <span className="font-bold text-strand-gold">{step.label}</span>
          <span className="text-zinc-500">|</span>
          <span className="text-zinc-300 font-medium">{step.subLabel}</span>
        </div>
      </Html>
    </mesh>
  );
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 15, 10]} intensity={1.8} color={0xfff6d6} />
      <pointLight position={[0, 0, 0]} intensity={2.2} color={0xffd700} distance={20} />
      <pointLight position={[-10, 5, -2]} intensity={1.2} color={0xffc400} distance={15} />
      <pointLight position={[10, -5, -2]} intensity={1.2} color={0xffea80} distance={15} />

      {/* 3D Moving Strand Bundle */}
      <StrandBundleMesh />

      {/* Agent Step Checkpoints anchored directly ON the main strand */}
      {AGENT_STEPS.map((step) => (
        <AnchoredAgentStepNode key={step.id} step={step} />
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
        camera={{ position: [0, 0, 8.5], fov: 48 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        dpr={[1, 2]}
      >
        <Scene />
      </Canvas>
      {/* Subtle bottom vignette for terminal and dashboard readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-surface-page via-transparent to-surface-page/30" />
    </div>
  );
}
