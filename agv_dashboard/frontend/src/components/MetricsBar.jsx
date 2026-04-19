/**
 * MetricsBar.jsx
 *
 * Top strip: connection status, current speed, active zone,
 * mission state, and session uptime.
 */

import { ZONE_META, MISSION_STEPS } from '../hooks/useAGVSocket'

const styles = {
  bar: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr 1fr 1fr auto',
    gap: '1px',
    background: 'var(--border-dim)',
    borderBottom: '1px solid var(--border)',
  },
  cell: {
    background: 'var(--bg-card)',
    padding: '14px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  label: {
    fontFamily: 'var(--font-sans)',
    fontSize: '10px',
    fontWeight: 500,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: 'var(--text-dim)',
  },
  value: {
    fontFamily: 'var(--font-mono)',
    fontSize: '20px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    lineHeight: 1,
  },
  unit: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginLeft: '4px',
  },
  connDot: (connected) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: connected ? 'var(--safe)' : 'var(--stop)',
    flexShrink: 0,
    animation: connected ? 'blink 2s ease-in-out infinite' : 'none',
  }),
  connRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '2px',
  },
  connText: (connected) => ({
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: connected ? 'var(--safe)' : 'var(--stop)',
  }),
  speedBar: {
    height: '3px',
    background: 'var(--border)',
    borderRadius: '2px',
    marginTop: '6px',
    overflow: 'hidden',
  },
  speedFill: (pct, zone) => ({
    height: '100%',
    width: `${Math.min(100, pct)}%`,
    background: ZONE_META[zone]?.color ?? 'var(--blue)',
    borderRadius: '2px',
    transition: 'width 0.8s ease, background 0.4s ease',
  }),
  missionBadge: (state) => {
    const idx        = MISSION_STEPS.indexOf(state)
    const pct        = idx < 0 ? 0 : Math.round((idx / (MISSION_STEPS.length - 1)) * 100)
    return {
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: '4px',
      background: 'var(--blue-bg)',
      border: '1px solid rgba(59,130,246,0.3)',
      fontFamily: 'var(--font-mono)',
      fontSize: '11px',
      color: 'var(--blue)',
      marginTop: '2px',
    }
  },
}

function formatUptime(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export default function MetricsBar({ data }) {
  const { connected, currentSpeed, speedLimit, zone, zoneName, missionState, uptime } = data
  const zoneMeta   = ZONE_META[zone] ?? ZONE_META.SAFE
  const speedPct   = speedLimit > 0 ? (currentSpeed / speedLimit) * 100 : 0

  return (
    <div style={styles.bar}>

      {/* Connection */}
      <div style={styles.cell}>
        <span style={styles.label}>Status</span>
        <div style={styles.connRow}>
          <div style={styles.connDot(connected)} />
          <span style={styles.connText(connected)}>
            {connected ? 'CONNECTED' : 'OFFLINE'}
          </span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>
          AGV-001
        </span>
      </div>

      {/* Speed */}
      <div style={styles.cell}>
        <span style={styles.label}>Current speed</span>
        <div>
          <span style={{ ...styles.value, color: zoneMeta.color, transition: 'color 0.4s ease' }}>
            {currentSpeed.toFixed(2)}
          </span>
          <span style={styles.unit}>m/s</span>
        </div>
        <div style={styles.speedBar}>
          <div style={styles.speedFill(speedPct, zone)} />
        </div>
      </div>

      {/* Zone */}
      <div style={{ ...styles.cell, borderLeft: `2px solid ${zoneMeta.color}`, transition: 'border-color 0.4s ease' }}>
        <span style={styles.label}>Safety zone</span>
        <span style={{ ...styles.value, fontSize: '15px', color: zoneMeta.color, transition: 'color 0.4s ease', marginTop: '2px' }}>
          {zone}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)' }}>
          {zoneName} · max {speedLimit.toFixed(1)} m/s
        </span>
      </div>

      {/* Mission */}
      <div style={styles.cell}>
        <span style={styles.label}>Mission state</span>
        <span style={styles.missionBadge(missionState)}>
          {missionState}
        </span>
      </div>

      {/* Uptime */}
      <div style={styles.cell}>
        <span style={styles.label}>Session</span>
        <span style={{ ...styles.value, fontSize: '18px' }}>
          {formatUptime(uptime)}
        </span>
      </div>

    </div>
  )
}
