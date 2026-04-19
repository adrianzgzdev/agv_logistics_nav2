/**
 * useAGVSocket.js
 *
 * Custom hook that provides AGV telemetry state.
 *
 * MOCK MODE (default, MOCK_MODE = true):
 *   Simulates a full mission cycle with realistic zone transitions
 *   and position updates. No backend required — perfect for demo recording.
 *
 * LIVE MODE (MOCK_MODE = false):
 *   Connects to the FastAPI WebSocket at ws://localhost:8000/ws
 *   and streams real ROS 2 data from ros_bridge.py.
 *
 * Toggle MOCK_MODE here or via ?mock=false in the URL query string.
 */

import { useState, useEffect, useRef, useCallback } from 'react'

// ── Toggle this to switch between mock and live backend ──────────────────────
const MOCK_MODE = false

// ── Warehouse layout: waypoints the AGV visits during a demo mission ─────────
// Coordinates map to the SVG viewBox used in AGVMap.jsx (0..500 x 0..320)
const WAYPOINTS = [
  { x: 390, y: 260, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'IDLE',              speedVal: 0.00 },
  { x: 320, y: 220, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'APPROACHING_PICKUP', speedVal: 0.85 },
  { x: 220, y: 180, zone: 'SLOW',   zoneName: 'loading_bay',    speed: 0.3,  missionState: 'APPROACHING_PICKUP', speedVal: 0.28 },
  { x: 160, y: 150, zone: 'SLOW',   zoneName: 'loading_bay',    speed: 0.3,  missionState: 'MOVING_TO_PICKUP',   speedVal: 0.22 },
  { x: 120, y: 130, zone: 'SLOW',   zoneName: 'loading_bay',    speed: 0.3,  missionState: 'MOVING_TO_PICKUP',   speedVal: 0.15 },
  { x: 100, y: 120, zone: 'SLOW',   zoneName: 'loading_bay',    speed: 0.3,  missionState: 'LOADING',            speedVal: 0.00 },
  { x: 100, y: 120, zone: 'SLOW',   zoneName: 'loading_bay',    speed: 0.3,  missionState: 'LOADING',            speedVal: 0.00 },
  { x: 160, y: 170, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.70 },
  { x: 280, y: 190, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.90 },
  { x: 370, y: 110, zone: 'STOP',   zoneName: 'forklift_area',  speed: 0.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.00 },
  { x: 370, y: 110, zone: 'STOP',   zoneName: 'forklift_area',  speed: 0.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.00 },
  { x: 340, y: 150, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.65 },
  { x: 400, y: 200, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'MOVING_TO_DROPOFF',  speedVal: 0.80 },
  { x: 440, y: 240, zone: 'SAFE',   zoneName: 'dropoff_zone',   speed: 1.0,  missionState: 'UNLOADING',          speedVal: 0.00 },
  { x: 440, y: 240, zone: 'SAFE',   zoneName: 'dropoff_zone',   speed: 1.0,  missionState: 'COMPLETED',          speedVal: 0.00 },
  { x: 390, y: 260, zone: 'SAFE',   zoneName: 'main_corridor',  speed: 1.0,  missionState: 'IDLE',               speedVal: 0.00 },
]

// ── Mission steps in order ───────────────────────────────────────────────────
export const MISSION_STEPS = [
  'IDLE',
  'APPROACHING_PICKUP',
  'MOVING_TO_PICKUP',
  'LOADING',
  'MOVING_TO_DROPOFF',
  'UNLOADING',
  'COMPLETED',
]

// ── Zone color map (shared with components) ───────────────────────────────────
export const ZONE_META = {
  SAFE:       { color: '#22c55e', label: 'Safe',       bgVar: '--safe-bg',       borderVar: '--safe-border'       },
  SLOW:       { color: '#f59e0b', label: 'Slow zone',  bgVar: '--slow-bg',       borderVar: '--slow-border'       },
  STOP:       { color: '#ef4444', label: 'Stop',       bgVar: '--stop-bg',       borderVar: '--stop-border'       },
  RESTRICTED: { color: '#a855f7', label: 'Restricted', bgVar: '--restricted-bg', borderVar: '--restricted-border' },
}

// ── Default / initial telemetry state ────────────────────────────────────────
const INITIAL_STATE = {
  connected:    false,
  pose:         { x: 390, y: 260, yaw: 0 },
  zone:         'SAFE',
  zoneName:     'main_corridor',
  speedLimit:   1.0,
  currentSpeed: 0.0,
  missionState: 'IDLE',
  events:       [],
  uptime:       0,
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function now() {
  return new Date().toLocaleTimeString('en-GB', { hour12: false })
}

function makeEvent(zone, zoneName) {
  return { time: now(), zone, zoneName, id: Date.now() + Math.random() }
}

// ── MOCK simulation ──────────────────────────────────────────────────────────
function useMockAGV() {
  const [state, setState] = useState({
    ...INITIAL_STATE,
    connected: true,
    events: [makeEvent('SAFE', 'main_corridor')],
  })

  const stepRef    = useRef(0)
  const uptimeRef  = useRef(0)

  useEffect(() => {
    // Uptime counter
    const uptimeTick = setInterval(() => {
      uptimeRef.current += 1
      setState(s => ({ ...s, uptime: uptimeRef.current }))
    }, 1000)

    // Waypoint stepper — advances every 2.5 s
    const waypointTick = setInterval(() => {
      stepRef.current = (stepRef.current + 1) % WAYPOINTS.length
      const wp = WAYPOINTS[stepRef.current]

      setState(prev => {
        const zoneChanged = wp.zone !== prev.zone || wp.zoneName !== prev.zoneName
        const newEvents   = zoneChanged
          ? [makeEvent(wp.zone, wp.zoneName), ...prev.events].slice(0, 40)
          : prev.events

        return {
          ...prev,
          pose:         { x: wp.x, y: wp.y, yaw: 0 },
          zone:         wp.zone,
          zoneName:     wp.zoneName,
          speedLimit:   wp.speed,
          currentSpeed: wp.speedVal,
          missionState: wp.missionState,
          events:       newEvents,
        }
      })
    }, 2500)

    return () => {
      clearInterval(uptimeTick)
      clearInterval(waypointTick)
    }
  }, [])

  return state
}

// ── LIVE WebSocket connection ─────────────────────────────────────────────────
function useLiveAGV() {
  const [state, setState] = useState(INITIAL_STATE)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws

    ws.onopen = () => setState(s => ({ ...s, connected: true }))

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setState(prev => {
          const zoneChanged =
            data.zone !== prev.zone || data.zone_name !== prev.zoneName
          const newEvents = zoneChanged
            ? [makeEvent(data.zone, data.zone_name), ...prev.events].slice(0, 40)
            : prev.events

          return {
            ...prev,
            pose:         { x: data.pose_x ?? prev.pose.x, y: data.pose_y ?? prev.pose.y, yaw: data.pose_yaw ?? 0 },
            zone:         data.zone        ?? prev.zone,
            zoneName:     data.zone_name   ?? prev.zoneName,
            speedLimit:   data.speed_limit ?? prev.speedLimit,
            currentSpeed: data.current_speed ?? prev.currentSpeed,
            missionState: data.mission_state ?? prev.missionState,
            uptime:       data.uptime ?? prev.uptime,
            events:       newEvents,
          }
        })
      } catch (e) {
        console.warn('[useAGVSocket] Failed to parse message:', e)
      }
    }

    ws.onclose = () => {
      setState(s => ({ ...s, connected: false }))
      setTimeout(connect, 3000)   // auto-reconnect
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return state
}

// ── Public hook — switch here or via URL param ────────────────────────────────
export function useAGVSocket() {
  const urlParams  = new URLSearchParams(window.location.search)
  const forceLive  = urlParams.get('mock') === 'false'
  const mockActive = MOCK_MODE && !forceLive

  const mockState = useMockAGV()
  const liveState = useLiveAGV()

  // Always call both hooks (Rules of Hooks), return only the active one
  return mockActive ? mockState : liveState
}
