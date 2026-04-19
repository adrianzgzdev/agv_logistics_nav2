/**
 * AGVMap.jsx — real zones from zones.yaml as SVG polygons
 */

import { ZONE_META } from '../hooks/useAGVSocket'

const ROS_X_MIN = -5.0, ROS_X_MAX = 3.0
const ROS_Y_MIN = -2.5, ROS_Y_MAX = 8.5
const SVG_W = 500, SVG_H = 320, PAD = 30

function rosToSvg(rosX, rosY) {
  const sx = PAD + ((ROS_X_MAX - rosX) / (ROS_X_MAX - ROS_X_MIN)) * (SVG_W - PAD * 2)
  const sy = PAD + ((ROS_Y_MAX - rosY) / (ROS_Y_MAX - ROS_Y_MIN)) * (SVG_H - PAD * 2)
  return { x: sx, y: sy }
}

function polyPoints(polygon) {
  return polygon.map(([x, y]) => {
    const p = rosToSvg(x, y)
    return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
  }).join(' ')
}

function centroid(polygon) {
  const cx = polygon.reduce((s, [x]) => s + x, 0) / polygon.length
  const cy = polygon.reduce((s, [, y]) => s + y, 0) / polygon.length
  return rosToSvg(cx, cy)
}

const ZONES = [
  {
    id: 'picking_corridor_entry', label: 'picking_corridor', type: 'SLOW',
    polygon: [[-2.5, 4.2], [2.5, 4.2], [2.5, 5.3], [-2.5, 5.3]],
  },
  {
    id: 'pallet_pickup_zone', label: 'pallet_pickup', type: 'STOP',
    polygon: [[-1.0, 5.3], [1.5, 5.3], [1.5, 6.3], [-1.0, 6.3]],
  },
  {
    id: 'dispatch_dropoff_zone', label: 'dispatch_dropoff', type: 'SLOW',
    polygon: [[-1.5, -0.8], [1.5, -0.8], [1.5, 1.2], [-1.5, 1.2]],
  },
  {
    id: 'warehouse_perimeter', label: 'perimeter', type: 'RESTRICTED',
    polygon: [[-4.5, -2.0], [-3.0, -2.0], [-3.0, 8.0], [-4.5, 8.0]],
  },
]

function ZonePolygon({ zone, isActive }) {
  const meta = ZONE_META[zone.type] ?? ZONE_META['SAFE']
  const c = centroid(zone.polygon)
  return (
    <g>
      <polygon
        points={polyPoints(zone.polygon)}
        fill={meta.color} fillOpacity={isActive ? 0.18 : 0.07}
        stroke={meta.color} strokeOpacity={isActive ? 0.75 : 0.28}
        strokeWidth={isActive ? 1.5 : 0.8}
        strokeDasharray={zone.type === 'SAFE' ? 'none' : '5,3'}
        style={{ transition: 'fill-opacity 0.4s ease, stroke-opacity 0.4s ease' }}
      />
      <text x={c.x} y={c.y - 5} textAnchor="middle"
        fontFamily="'IBM Plex Mono', monospace" fontSize="9"
        fill={meta.color} fillOpacity={0.9}>{zone.type}</text>
      <text x={c.x} y={c.y + 7} textAnchor="middle"
        fontFamily="'IBM Plex Mono', monospace" fontSize="7"
        fill={meta.color} fillOpacity={0.55}>{zone.label}</text>
    </g>
  )
}

function AGVDot({ x, y, zone }) {
  const color = ZONE_META[zone]?.color ?? '#22c55e'
  return (
    <g transform={`translate(${x},${y})`}
       style={{ transition: 'transform 0.7s cubic-bezier(0.4,0,0.2,1)' }}>
      <circle r="12" fill="none" stroke={color} strokeWidth="1" opacity="0.3"
        style={{ animation: 'pulse-ring 1.8s ease-out infinite' }} />
      <circle r="7" fill={color} fillOpacity="0.15" stroke={color} strokeWidth="1" strokeOpacity="0.5"/>
      <circle r="4" fill={color}/>
      <line x1="0" y1="-4" x2="0" y2="-9" stroke={color} strokeWidth="1.5" strokeLinecap="round"/>
    </g>
  )
}

export default function AGVMap({ pose, zone, zoneName }) {
  const { x: rosX, y: rosY, yaw } = pose
  const svgPos = rosToSvg(rosX, rosY)

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: '8px', overflow: 'hidden',
      flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0,
    }}>
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)',
        }}>Position map</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)' }}>
          x={rosX.toFixed(2)} · y={rosY.toFixed(2)} · yaw={yaw.toFixed(2)}
        </span>
      </div>

      <svg viewBox="0 0 500 320" width="100%" height="100%"
           style={{ display: 'block', padding: '8px', flex: 1 }}>
        <rect x={PAD} y={PAD} width={SVG_W - PAD * 2} height={SVG_H - PAD * 2}
          rx="6" fill="none" stroke="var(--border)" strokeWidth="0.8" strokeDasharray="8,4"/>
        {ZONES.map(z => (
          <ZonePolygon key={z.id} zone={z} isActive={z.id === zoneName} />
        ))}
        <AGVDot x={svgPos.x} y={svgPos.y} zone={zone} />
      </svg>
    </div>
  )
}
