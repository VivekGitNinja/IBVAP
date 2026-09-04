import React, { useState, useEffect } from 'react';
import { playTacticalTone } from '../utils/audio';
import type { Page } from '../store/useTacticalStore';

export interface PatrolStep {
  id: number;
  title: string;
  page: Page;
  description: string;
  durationSec: number;
}

export const PATROL_STEPS: PatrolStep[] = [
  {
    id: 1,
    title: 'CCTV Reconnaissance Matrix',
    page: 'cameras',
    description: 'Physical IP & USB edge camera nodes with real link diagnostics and low-latency streams.',
    durationSec: 8,
  },
  {
    id: 2,
    title: 'Edge CV & Virtual Fence Studio',
    page: 'media',
    description: 'Real video analysis, tripwires, polygon virtual fences, and multi-object centroid tracking.',
    durationSec: 8,
  },
  {
    id: 3,
    title: 'Perimeter Intrusion Triage',
    page: 'incidents',
    description: 'Autonomous security incident escalation with explainable reason codes and track correlation.',
    durationSec: 8,
  },
  {
    id: 4,
    title: 'BSA 2023 §63 Evidence Vault',
    page: 'evidence',
    description: 'Cryptographic SHA-256 evidence sealing under Bharatiya Sakshya Adhiniyam, 2023 Section 63.',
    durationSec: 8,
  },
  {
    id: 5,
    title: 'Geospatial Situational Map',
    page: 'map',
    description: 'Air-gapped base map with camera FOV bearing cones, sector filters, and pulsing incident markers.',
    durationSec: 8,
  },
  {
    id: 6,
    title: 'Court-Ready Forensic Report',
    page: 'media',
    description: 'Tamper-evident JSON and native PDF 1.4 report generation certified under Indian evidence law.',
    durationSec: 8,
  },
];

interface PatrolModeProps {
  isActive: boolean;
  onClose: () => void;
  onNavigate: (page: Page) => void;
}

export function PatrolMode({ isActive, onClose, onNavigate }: PatrolModeProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const step = PATROL_STEPS[currentStepIndex];

  // ESC key listener to exit patrol mode
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        playTacticalTone('click');
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isActive, onClose]);

  // Navigate when step changes
  useEffect(() => {
    if (!isActive) return;
    onNavigate(step.page);
  }, [currentStepIndex, isActive]);

  // Auto-progression timer
  useEffect(() => {
    if (!isActive || isPaused) return;

    const timer = setInterval(() => {
      setElapsed((prev) => {
        if (prev + 1 >= step.durationSec) {
          // Advance to next step
          setCurrentStepIndex((curr) => (curr + 1) % PATROL_STEPS.length);
          playTacticalTone('click');
          return 0;
        }
        return prev + 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isActive, isPaused, currentStepIndex, step.durationSec]);

  if (!isActive) return null;

  const progressPct = ((elapsed / step.durationSec) * 100).toFixed(0);

  const handleNext = () => {
    playTacticalTone('click');
    setElapsed(0);
    setCurrentStepIndex((curr) => (curr + 1) % PATROL_STEPS.length);
  };

  const handlePrev = () => {
    playTacticalTone('click');
    setElapsed(0);
    setCurrentStepIndex((curr) => (curr - 1 + PATROL_STEPS.length) % PATROL_STEPS.length);
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        width: '90%',
        maxWidth: 720,
        background: 'rgba(8, 14, 26, 0.95)',
        border: '1px solid #00f0ff',
        borderRadius: 8,
        padding: '12px 16px',
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.25)',
        fontFamily: 'var(--font-mono)',
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Top Header Strip */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="rec-dot" style={{ background: '#00f0ff' }} />
          <span style={{ fontSize: 11, fontWeight: 800, color: '#00f0ff', letterSpacing: 0.5 }}>
            TACTICAL PATROL MODE — STOP {step.id} / {PATROL_STEPS.length}
          </span>
          <span
            style={{
              fontSize: 9,
              background: 'rgba(0, 255, 157, 0.15)',
              color: '#00ff9d',
              padding: '1px 5px',
              borderRadius: 3,
              border: '1px solid #00ff9d',
            }}
          >
            REAL DATA ONLY
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setIsPaused(!isPaused)}
            style={{
              background: isPaused ? 'rgba(255, 170, 0, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              color: isPaused ? '#ffaa00' : '#fff',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              padding: '3px 8px',
              borderRadius: 3,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button
            onClick={handlePrev}
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              padding: '3px 8px',
              borderRadius: 3,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            ◀ Prev
          </button>
          <button
            onClick={handleNext}
            style={{
              background: 'rgba(0, 240, 255, 0.2)',
              color: '#00f0ff',
              border: '1px solid #00f0ff',
              padding: '3px 8px',
              borderRadius: 3,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            Next ▶
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 42, 85, 0.2)',
              color: '#ff2a55',
              border: '1px solid #ff2a55',
              padding: '3px 8px',
              borderRadius: 3,
              fontSize: 10,
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
            title="Exit Patrol Mode (ESC)"
          >
            ✕ Exit (ESC)
          </button>
        </div>
      </div>

      {/* Step Description */}
      <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', marginBottom: 2 }}>{step.title}</div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>{step.description}</div>

      {/* Progress Bar */}
      <div style={{ height: 4, background: 'rgba(255, 255, 255, 0.1)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${progressPct}%`,
            background: 'linear-gradient(90deg, #00f0ff, #00ff9d)',
            transition: 'width 1s linear',
          }}
        />
      </div>
    </div>
  );
}
