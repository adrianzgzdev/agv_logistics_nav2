/**
 * App.jsx
 *
 * Main dashboard layout.
 *
 * ┌─────────────────────────────────────────────────────────┐
 * │  MetricsBar  (top strip — 5 KPI cells)                  │
 * ├──────────────────────────┬──────────────────────────────┤
 * │  AGVMap                  │  MissionPanel                │
 * │  (warehouse SVG)         │  (step tracker)              │
 * ├──────────────────────────┴──────────────────────────────┤
 * │  EventLog   (scrollable safety event feed)              │
 * └─────────────────────────────────────────────────────────┘
 */

import { useAGVSocket } from './hooks/useAGVSocket'
import MetricsBar  from './components/MetricsBar'
import AGVMap      from './components/AGVMap'
import MissionPanel from './components/MissionPanel'
import EventLog    from './components/EventLog'

export default function App() {
  const agv = useAGVSocket()

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      overflow: 'hidden',
      background: 'var(--bg-base)',
    }}>

      {/* ── Top header bar ── */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        height: '44px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Logo mark */}
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect x="2" y="2" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.8"/>
            <rect x="11" y="2" width="7" height="7" rx="1.5" fill="#22c55e" fillOpacity="0.8"/>
            <rect x="2" y="11" width="7" height="7" rx="1.5" fill="#f59e0b" fillOpacity="0.8"/>
            <rect x="11" y="11" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.4"/>
          </svg>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            fontWeight: 500,
            color: 'var(--text-primary)',
            letterSpacing: '0.02em',
          }}>
            AGV Fleet Dashboard
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-secondary)',
            paddingLeft: '4px',
          }}>
            agv_logistics_nav2 · Project 4
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-secondary)',
          }}>
            ROS 2 Jazzy · Nav2 · FastAPI
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            padding: '2px 8px',
            borderRadius: '3px',
            background: 'rgba(245,158,11,0.1)',
            border: '1px solid rgba(245,158,11,0.25)',
            color: '#f59e0b',
          }}>
            MOCK MODE
          </span>
        </div>
      </header>

      {/* ── Metrics strip ── */}
      <MetricsBar data={agv} />

      {/* ── Main content ── */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr 280px',
        gridTemplateRows: 'minmax(0, 1fr) 200px',
        gap: '1px',
        background: 'var(--border-dim)',
        overflow: 'auto',
      }}>

        {/* Map */}
        <div style={{
          background: 'var(--bg-base)',
          padding: '16px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'stretch',
        }}>
          <AGVMap
            pose={agv.pose}
            zone={agv.zone}
            zoneName={agv.zoneName}
          />
        </div>

        {/* Mission panel */}
        <div style={{
          background: 'var(--bg-base)',
          padding: '16px 16px 16px 0',
          overflowY: 'auto',
        }}>
          <MissionPanel missionState={agv.missionState} />
        </div>

        {/* Event log — full width bottom */}
        <div style={{
          gridColumn: '1 / -1',
          background: 'var(--bg-base)',
          padding: '0 16px 16px',
        }}>
          <EventLog events={agv.events} />
        </div>

      </div>
    </div>
  )
}
