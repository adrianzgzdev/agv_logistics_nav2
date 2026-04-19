/**
 * EventLog.jsx
 *
 * Live scrolling feed of safety zone transition events.
 * New events slide in at the top. Auto-limited to 40 entries.
 */

import { ZONE_META } from '../hooks/useAGVSocket'

const BADGE_STYLES = {
  SAFE:       { background: 'rgba(34,197,94,0.12)',   color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)'   },
  SLOW:       { background: 'rgba(245,158,11,0.12)',  color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)'  },
  STOP:       { background: 'rgba(239,68,68,0.12)',   color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)'   },
  RESTRICTED: { background: 'rgba(168,85,247,0.12)',  color: '#a855f7', border: '1px solid rgba(168,85,247,0.3)'  },
}

function EventRow({ event, isNew }) {
  const badge = BADGE_STYLES[event.zone] ?? BADGE_STYLES.SAFE

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '52px 72px 1fr',
      gap: '10px',
      alignItems: 'center',
      padding: '7px 16px',
      borderBottom: '1px solid var(--border-dim)',
      animation: isNew ? 'slideIn 0.25s ease' : 'none',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-dim)',
        flexShrink: 0,
      }}>
        {event.time}
      </span>

      <span style={{
        ...badge,
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        fontWeight: 500,
        padding: '2px 6px',
        borderRadius: '3px',
        textAlign: 'center',
        flexShrink: 0,
      }}>
        {event.zone}
      </span>

      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-secondary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {event.zoneName}
      </span>
    </div>
  )
}

export default function EventLog({ events }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>

      {/* Header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexShrink: 0,
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--text-dim)',
        }}>
          Safety event log
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          color: 'var(--text-dim)',
        }}>
          {events.length} events
        </span>
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '52px 72px 1fr',
        gap: '10px',
        padding: '5px 16px',
        borderBottom: '1px solid var(--border-dim)',
        flexShrink: 0,
      }}>
        {['time', 'zone', 'location'].map(h => (
          <span key={h} style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '9px',
            fontWeight: 500,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-dim)',
          }}>
            {h}
          </span>
        ))}
      </div>

      {/* Event rows */}
      <div style={{ overflowY: 'auto', maxHeight: '220px' }}>
        {events.length === 0 ? (
          <div style={{
            padding: '20px 16px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-dim)',
            textAlign: 'center',
          }}>
            Waiting for events...
          </div>
        ) : (
          events.map((evt, idx) => (
            <EventRow key={evt.id} event={evt} isNew={idx === 0} />
          ))
        )}
      </div>

    </div>
  )
}
