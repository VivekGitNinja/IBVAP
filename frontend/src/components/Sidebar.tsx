import React, { useState } from 'react';
import type { Alert } from '../types';
import type { Page } from '../store/useTacticalStore';
import { playTacticalTone } from '../utils/audio';

interface SidebarProps {
  page: Page;
  setPage: (p: Page) => void;
  alerts: Alert[];
  ws: string;
}

export function Sidebar({ page, setPage, alerts, ws }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('ibvap_sidebar_expanded') !== 'false';
    }
    return true;
  });

  const toggleSidebar = () => {
    const next = !isExpanded;
    setIsExpanded(next);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('ibvap_sidebar_expanded', String(next));
    }
    playTacticalTone('click');
  };

  const newAlerts = alerts.filter((a) => a.status === 'NEW').length;

  const groups: {
    category: string;
    items: { id: Page; label: string; iconSvg: React.ReactNode }[];
  }[] = [
    {
      category: 'COMMAND & RADAR',
      items: [
        {
          id: 'dashboard',
          label: 'C4ISR Command',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          ),
        },
        {
          id: 'map',
          label: 'Situational Map',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
          ),
        },
        {
          id: 'cameras',
          label: 'Tactical Matrix',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
          ),
        },
        {
          id: 'thermal',
          label: 'FLIR & Drone Recon',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <line x1="12" y1="3" x2="12" y2="7" />
              <line x1="12" y1="17" x2="12" y2="21" />
              <line x1="3" y1="12" x2="7" y2="12" />
              <line x1="17" y1="12" x2="21" y2="12" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          ),
        },
      ],
    },
    {
      category: 'AI PERCEPTION',
      items: [
        {
          id: 'media',
          label: 'Video Studio',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
          ),
        },
        {
          id: 'anpr',
          label: 'ANPR Checkpost',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="5" width="20" height="14" rx="2" />
              <path d="M7 10h10M7 14h6" />
              <circle cx="6" cy="18" r="1.5" />
              <circle cx="18" cy="18" r="1.5" />
            </svg>
          ),
        },
        {
          id: 'frs',
          label: 'FRS Biometrics',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
              <path d="M3 3h3v3M21 3h-3v3M3 21h3v-3M21 21h-3v-3" />
            </svg>
          ),
        },
        {
          id: 'qrt',
          label: 'QRT Patrols',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="13 10 10 14 14 14 11 18" />
            </svg>
          ),
        },
      ],
    },
    {
      category: 'DEFENSE INTEL',
      items: [
        {
          id: 'incidents',
          label: 'Threat Queue',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          ),
        },
        {
          id: 'evidence',
          label: 'Evidence Locker',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          ),
        },
        {
          id: 'audit',
          label: 'Audit Ledger',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          ),
        },
      ],
    },
    {
      category: 'SYSTEM CONTROL',
      items: [
        {
          id: 'health',
          label: 'Edge Diagnostics',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          ),
        },
        {
          id: 'demo',
          label: 'War Gaming',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          ),
        },
        {
          id: 'settings',
          label: 'Configuration',
          iconSvg: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          ),
        },
      ],
    },
  ];

  return (
    <nav className={`sidebar ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="sidebar-brand">
        <div className="brand-left">
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          {isExpanded && (
            <div className="brand-text">
              <div className="brand-name">SSB C4ISR</div>
              <div className="brand-sub">DEFENSE V2.0</div>
            </div>
          )}
        </div>
        <button
          className="sidebar-toggle-btn"
          onClick={toggleSidebar}
          title={isExpanded ? 'Collapse Navigation' : 'Expand Navigation'}
        >
          {isExpanded ? '◀' : '▶'}
        </button>
      </div>

      <div className="sidebar-items">
        {groups.map((grp, gIdx) => (
          <React.Fragment key={gIdx}>
            {isExpanded && <div className="sidebar-category">{grp.category}</div>}
            {grp.items.map((it) => (
              <button
                key={it.id}
                className={`sidebar-item${page === it.id ? ' active' : ''}`}
                onClick={() => {
                  playTacticalTone('click');
                  setPage(it.id);
                }}
                title={!isExpanded ? it.label : undefined}
              >
                <span className="sidebar-icon">{it.iconSvg}</span>
                <span className="sidebar-label">{it.label}</span>
                {it.id === 'incidents' && newAlerts > 0 && (
                  <span className="badge">{newAlerts}</span>
                )}
              </button>
            ))}
          </React.Fragment>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className={`ws-dot ${ws}`} />
        <span className="ws-label">{ws.toUpperCase()}</span>
        {isExpanded && <div className="sidebar-copy">MHA • SIH 2026</div>}
      </div>
    </nav>
  );
}
