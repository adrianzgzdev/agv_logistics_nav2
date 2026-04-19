/**
 * MissionPanel.jsx
 *
 * Vertical mission step tracker.
 * Shows all mission states, highlights the current one,
 * and marks completed steps.
 */

import { MISSION_STEPS } from '../hooks/useAGVSocket'

const STATE_DESCRIPTIONS = {
  IDLE:               'Waiting for mission assignment',
  APPROACHING_PICKUP: 'Navigating toward pickup approach pose',
  MOVING_TO_PICKUP:   'Final approach — entering loading bay',
  LOADING:            'Loading sequence in progress',
  MOVING_TO_DROPOFF:  'Navigating toward dropoff zone',
  UNLOADING:          'Unloading sequence in progress',
  COMPLETED:          'Mission completed successfully',
}

export default function MissionPanel({ missionState }) {
  const currentIdx = MISSION_STEPS.indexOf(missionState)

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>

      {/* Header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--text-dim)',
        }}>
          Mission sequence
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          color: 'var(--blue)',
        }}>
          {currentIdx + 1} / {MISSION_STEPS.length}
        </span>
      </div>

      {/* Steps */}
      <div style={{ padding: '8px 0' }}>
        {MISSION_STEPS.map((step, idx) => {
          const isDone    = idx < currentIdx
          const isActive  = idx === currentIdx
          const isPending = idx > currentIdx

          let dotColor  = 'var(--text-dim)'
          let textColor = 'var(--text-dim)'
          let bgColor   = 'transparent'
          let borderL   = '2px solid transparent'

          if (isDone) {
            dotColor  = 'var(--safe)'
            textColor = 'var(--text-secondary)'
          }
          if (isActive) {
            dotColor  = 'var(--blue)'
            textColor = 'var(--text-primary)'
            bgColor   = 'rgba(59,130,246,0.06)'
            borderL   = '2px solid var(--blue)'
          }

          return (
            <div
              key={step}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '8px 16px',
                background: bgColor,
                borderLeft: borderL,
                transition: 'background 0.3s ease, border-color 0.3s ease',
                animation: isActive ? 'slideIn 0.3s ease' : 'none',
              }}
            >
              {/* Dot + connector */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '3px', flexShrink: 0 }}>
                <div style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: dotColor,
                  flexShrink: 0,
                  transition: 'background 0.3s ease',
                  boxShadow: isActive ? `0 0 6px ${dotColor}` : 'none',
                }} />
                {idx < MISSION_STEPS.length - 1 && (
                  <div style={{
                    width: '1px',
                    height: '22px',
                    background: isDone ? 'var(--safe)' : 'var(--border)',
                    opacity: isDone ? 0.4 : 0.5,
                    marginTop: '3px',
                    transition: 'background 0.3s ease',
                  }} />
                )}
              </div>

              {/* Text */}
              <div style={{ paddingBottom: idx < MISSION_STEPS.length - 1 ? '10px' : 0 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: isActive ? 500 : 400,
                  color: textColor,
                  transition: 'color 0.3s ease',
                }}>
                  {step}
                </div>
                {isActive && (
                  <div style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: '10px',
                    color: 'var(--text-secondary)',
                    marginTop: '2px',
                    animation: 'fadeIn 0.3s ease',
                  }}>
                    {STATE_DESCRIPTIONS[step]}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
