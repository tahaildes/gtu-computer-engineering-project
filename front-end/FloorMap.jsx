// FloorMap.jsx — Top-down factory floor SVG
// Requires: window.DFSim

function FloorMap({ sensor, compressor, actuator, onMachineClick }) {
  const { STATE_COLORS, ALARM_COLORS } = window.DFSim;

  const compState  = (compressor && compressor.state) || 'NORMAL';
  const alarm      = (sensor && sensor.alarm) || 'OK';
  const machColor  = STATE_COLORS[compState] || STATE_COLORS.NORMAL;
  const sensColor  = ALARM_COLORS[alarm]     || ALARM_COLORS.OK;
  const fanSpeed   = (actuator && actuator.fan_pct) || 0;
  const ventAngle  = (actuator && actuator.sg90_angle) || 0;

  // Vent slit opening (0-1 ratio)
  const ventOpen = ventAngle / 180;

  return (
    <svg
      viewBox="0 0 760 520"
      style={{ width: '100%', height: '100%', display: 'block' }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Floor grid */}
        <pattern id="fm-grid" width="32" height="32" patternUnits="userSpaceOnUse">
          <path d="M32,0 L0,0 0,32" fill="none" stroke="rgba(255,200,120,0.045)" strokeWidth="0.7"/>
        </pattern>
        {/* Machine glow */}
        <filter id="fm-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="6" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        {/* Soft glow small */}
        <filter id="fm-glow-sm" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="3" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        {/* Hatch pattern for machine body */}
        <pattern id="fm-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(255,200,100,0.07)" strokeWidth="3"/>
        </pattern>
        {/* Hatch for actuator */}
        <pattern id="fm-hatch2" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(180,160,120,0.06)" strokeWidth="3"/>
        </pattern>
      </defs>

      {/* ── FLOOR ── */}
      <rect x="28" y="28" width="704" height="464" fill="#0d0b09"/>
      <rect x="28" y="28" width="704" height="464" fill="url(#fm-grid)"/>

      {/* ── OUTER WALLS ── */}
      {/* North wall */}
      <rect x="28" y="28" width="704" height="14" fill="#1e1a15"/>
      {/* South wall (with door gap 310-450) */}
      <rect x="28" y="478" width="282" height="14" fill="#1e1a15"/>
      <rect x="450" y="478" width="282" height="14" fill="#1e1a15"/>
      {/* West wall */}
      <rect x="28" y="28" width="14" height="464" fill="#1e1a15"/>
      {/* East wall */}
      <rect x="718" y="28" width="14" height="464" fill="#1e1a15"/>

      {/* Wall border lines (inner edge) */}
      <line x1="42" y1="42" x2="718" y2="42" stroke="#2e2820" strokeWidth="1"/>
      <line x1="42" y1="42" x2="42" y2="478" stroke="#2e2820" strokeWidth="1"/>
      <line x1="718" y1="42" x2="718" y2="478" stroke="#2e2820" strokeWidth="1"/>

      {/* ── DOOR ── */}
      <rect x="310" y="478" width="140" height="14" fill="#0d0b09"/>
      {/* Door arc suggestion */}
      <path d="M 310,478 Q 310,440 350,440" fill="none" stroke="#2e2820" strokeWidth="1" strokeDasharray="4,3"/>
      {/* Door threshold */}
      <line x1="310" y1="492" x2="450" y2="492" stroke="#3a3020" strokeWidth="2"/>

      {/* ── NORTH WALL — VENTILATION DUCTS ── */}
      {[130, 230, 330, 430, 530, 630].map((x, i) => (
        <g key={i}>
          <rect x={x} y="30" width="60" height="12" rx="2" fill="#151210"/>
          <rect x={x + 4} y="32" width="52" height="8" rx="1" fill="#0a0907"/>
          {/* Vent slits */}
          {[0,1,2,3,4].map(s => (
            <line key={s} x1={x + 8 + s * 9} y1="33" x2={x + 8 + s * 9} y2="39"
              stroke="#2a2418" strokeWidth="1.5"/>
          ))}
        </g>
      ))}

      {/* ── PIPE RUNS ── */}
      {/* North horizontal pipe */}
      <rect x="42" y="58" width="676" height="5" rx="2" fill="#1a1610"/>
      <rect x="42" y="59" width="676" height="3" rx="1" fill="#221e16"/>
      {/* West vertical pipe */}
      <rect x="58" y="42" width="5" height="436" rx="2" fill="#1a1610"/>
      {/* East vertical pipe */}
      <rect x="697" y="42" width="5" height="280" rx="2" fill="#1a1610"/>
      {/* Pipe joints */}
      {[58, 200, 340, 680].map((x, i) => (
        <circle key={i} cx={x + 2} cy="63" r="5" fill="#201c14" stroke="#2a2418" strokeWidth="1"/>
      ))}
      {[100, 200, 300, 380].map((y, i) => (
        <circle key={i} cx="61" cy={y} r="5" fill="#201c14" stroke="#2a2418" strokeWidth="1"/>
      ))}

      {/* ── FLOOR ZONE MARKINGS ── */}
      {/* Machine zone */}
      <rect x="430" y="100" width="240" height="220" rx="4"
        fill="none" stroke="rgba(255,160,30,0.08)" strokeWidth="1" strokeDasharray="6,4"/>
      {/* Actuator zone */}
      <rect x="75" y="310" width="260" height="140" rx="4"
        fill="none" stroke="rgba(160,140,100,0.08)" strokeWidth="1" strokeDasharray="6,4"/>
      {/* Safety floor markings */}
      <line x1="430" y1="100" x2="450" y2="100" stroke="rgba(255,160,30,0.15)" strokeWidth="2"/>
      <line x1="430" y1="100" x2="430" y2="120" stroke="rgba(255,160,30,0.15)" strokeWidth="2"/>
      <line x1="670" y1="320" x2="650" y2="320" stroke="rgba(255,160,30,0.15)" strokeWidth="2"/>
      <line x1="670" y1="320" x2="670" y2="300" stroke="rgba(255,160,30,0.15)" strokeWidth="2"/>

      {/* ── ESP32 #1 — SENSOR NODE ── */}
      <g transform="translate(68, 190)">
        {/* Wall mount bracket */}
        <rect x="-4" y="10" width="8" height="50" fill="#1a1610"/>
        {/* Device body */}
        <rect x="0" y="6" width="52" height="64" rx="3" fill="#18150f" stroke="#2e2820" strokeWidth="1.5"/>
        <rect x="3" y="9" width="46" height="58" rx="2" fill="url(#fm-hatch2)"/>
        {/* Sensor apertures */}
        <circle cx="14" cy="26" r="5" fill="#0d0b08" stroke="#2e2820" strokeWidth="1"/>
        <circle cx="28" cy="26" r="5" fill="#0d0b08" stroke="#2e2820" strokeWidth="1"/>
        <circle cx="42" cy="26" r="5" fill="#0d0b08" stroke="#2e2820" strokeWidth="1"/>
        {/* Status LED */}
        <circle cx="26" cy="54" r="5" fill={sensColor} opacity="0.9" filter="url(#fm-glow-sm)"
          style={{ animation: alarm !== 'OK' ? 'df-pulse 1.2s ease-in-out infinite' : 'none' }}/>
        <circle cx="26" cy="54" r="3" fill={sensColor}/>
        {/* Label */}
        <text x="26" y="82" textAnchor="middle" fill="#5a5040" fontSize="8" fontFamily="'IBM Plex Mono', monospace">ESP32 #1</text>
        <text x="26" y="92" textAnchor="middle" fill="#4a4030" fontSize="7" fontFamily="'IBM Plex Mono', monospace">SENSOR</text>
      </g>

      {/* ── ESP32 #2 — ACTUATOR CABINET ── */}
      <g transform="translate(80, 315)">
        {/* Shadow */}
        <rect x="4" y="4" width="248" height="128" rx="4" fill="rgba(0,0,0,0.5)"/>
        {/* Cabinet body */}
        <rect x="0" y="0" width="248" height="128" rx="4" fill="#14120d" stroke="#2a2418" strokeWidth="1.5"/>
        <rect x="3" y="3" width="242" height="122" rx="3" fill="url(#fm-hatch2)" opacity="0.5"/>
        {/* Front panel */}
        <rect x="8" y="10" width="232" height="108" rx="2" fill="#111009" stroke="#221e14" strokeWidth="1"/>

        {/* FAN CIRCLE */}
        <g transform="translate(38, 58)">
          <circle r="22" fill="#0d0b08" stroke="#2a2418" strokeWidth="1.5"/>
          <circle r="18" fill="none" stroke="#201c14" strokeWidth="1" strokeDasharray="3,2"/>
          {/* Fan blades - rotates when active */}
          <g style={{ transformOrigin: '0px 0px', animation: fanSpeed > 0 ? `df-spin ${1.2 - fanSpeed * 0.009}s linear infinite` : 'none' }}>
            <path d="M0,-14 Q6,-6 0,0 Q-6,-6 0,-14" fill={fanSpeed > 0 ? '#4a4030' : '#2a2418'}/>
            <path d="M14,0 Q6,6 0,0 Q6,-6 14,0" fill={fanSpeed > 0 ? '#4a4030' : '#2a2418'}/>
            <path d="M0,14 Q-6,6 0,0 Q6,6 0,14" fill={fanSpeed > 0 ? '#4a4030' : '#2a2418'}/>
            <path d="M-14,0 Q-6,-6 0,0 Q-6,6 -14,0" fill={fanSpeed > 0 ? '#4a4030' : '#2a2418'}/>
          </g>
          <circle r="4" fill="#1a1610" stroke="#2a2418" strokeWidth="1"/>
          <text y="32" textAnchor="middle" fill="#3a3428" fontSize="7" fontFamily="'IBM Plex Mono', monospace">{fanSpeed}%</text>
        </g>

        {/* VENT SERVO (SG90) */}
        <g transform="translate(100, 32)">
          <rect x="-18" y="-14" width="36" height="28" rx="2" fill="#0d0b08" stroke="#221e14" strokeWidth="1"/>
          {/* Vent slits that open with angle */}
          {[0,1,2].map(i => {
            const openH = Math.max(2, ventOpen * 8);
            return (
              <rect key={i} x={-13 + i * 10} y={-openH / 2} width="7" height={openH} rx="1"
                fill={ventOpen > 0.2 ? '#3a3020' : '#161310'} stroke="#2a2018" strokeWidth="0.5"/>
            );
          })}
          <text y="22" textAnchor="middle" fill="#3a3428" fontSize="7" fontFamily="'IBM Plex Mono', monospace">SG90 {ventAngle}°</text>
        </g>

        {/* AS100 SERVO */}
        <g transform="translate(154, 32)">
          <rect x="-14" y="-14" width="28" height="28" rx="2" fill="#0d0b08" stroke="#221e14" strokeWidth="1"/>
          {/* Rotation indicator */}
          <line x1="0" y1="0" x2={Math.cos((actuator?.as100_angle || 0) * Math.PI / 180 - Math.PI / 2) * 9}
            y2={Math.sin((actuator?.as100_angle || 0) * Math.PI / 180 - Math.PI / 2) * 9}
            stroke="#3a3428" strokeWidth="1.5"/>
          <circle cx="0" cy="0" r="3" fill="#1a1610"/>
          <text y="22" textAnchor="middle" fill="#3a3428" fontSize="7" fontFamily="'IBM Plex Mono', monospace">AS100</text>
        </g>

        {/* LED + MIST + BUZZER indicators */}
        <g transform="translate(198, 24)">
          <circle cx="0" cy="0" r="5" fill={actuator?.led ? '#f0e080' : '#1a1610'} stroke="#2a2418" strokeWidth="1"/>
          <text x="0" y="12" textAnchor="middle" fill="#3a3428" fontSize="6" fontFamily="'IBM Plex Mono', monospace">LED</text>
          <circle cx="20" cy="0" r="5" fill={actuator?.mist ? '#4090f0' : '#1a1610'} stroke="#2a2418" strokeWidth="1"/>
          <text x="20" y="12" textAnchor="middle" fill="#3a3428" fontSize="6" fontFamily="'IBM Plex Mono', monospace">MIST</text>
          <circle cx="10" cy="26" r="5"
            fill={actuator?.buzzer ? '#f07030' : '#1a1610'} stroke="#2a2418" strokeWidth="1"
            style={{ animation: actuator?.buzzer ? 'df-pulse 0.5s ease-in-out infinite' : 'none' }}/>
          <text x="10" y="38" textAnchor="middle" fill="#3a3428" fontSize="6" fontFamily="'IBM Plex Mono', monospace">BZZ</text>
        </g>

        {/* Label */}
        <text x="124" y="120" textAnchor="middle" fill="#4a4030" fontSize="9" fontFamily="'IBM Plex Mono', monospace">ESP32 #2 — ACTUATOR</text>
      </g>

      {/* ── ESP32 #3 — COMPRESSOR MACHINE ── */}
      <g
        transform="translate(435, 100)"
        onClick={onMachineClick}
        style={{ cursor: 'pointer' }}
        className="df-machine"
      >
        {/* Glow layer */}
        <rect x="-6" y="-6" width="252" height="232" rx="8"
          fill={machColor} opacity="0.06" filter="url(#fm-glow)"
          style={{ animation: compState === 'FAILURE' ? 'df-pulse 0.6s ease-in-out infinite' : compState === 'CRITICAL' ? 'df-pulse 1.0s ease-in-out infinite' : 'none' }}/>
        {/* Shadow */}
        <rect x="5" y="5" width="240" height="220" rx="6" fill="rgba(0,0,0,0.6)"/>
        {/* Main body */}
        <rect x="0" y="0" width="240" height="220" rx="6" fill="#16130e" stroke={machColor} strokeWidth="1.5" opacity="0.9"/>
        <rect x="3" y="3" width="234" height="214" rx="5" fill="url(#fm-hatch)" opacity="0.8"/>

        {/* ── MOTOR HOUSING (left) ── */}
        <rect x="10" y="15" width="95" height="110" rx="4" fill="#0f0d09" stroke="#2a2418" strokeWidth="1"/>
        <circle cx="57" cy="70" r="36" fill="#0a0907" stroke="#221e14" strokeWidth="1.5"/>
        <circle cx="57" cy="70" r="26" fill="none" stroke="#1e1a10" strokeWidth="1" strokeDasharray="4,3"/>
        <circle cx="57" cy="70" r="10" fill="#161210" stroke="#2a2418" strokeWidth="1"/>
        {/* Spinning rotor when running */}
        <g transform={`translate(57, 70)`}
          style={{ transformOrigin: '0px 0px', animation: compressor?.rpm > 200 ? `df-spin ${60 / (compressor?.rpm || 1460) * 8}s linear infinite` : 'none' }}>
          <line x1="0" y1="-22" x2="0" y2="22" stroke="#2e2820" strokeWidth="2.5"/>
          <line x1="-22" y1="0" x2="22" y2="0" stroke="#2e2820" strokeWidth="2.5"/>
          <line x1="-16" y1="-16" x2="16" y2="16" stroke="#2a2418" strokeWidth="1.5"/>
          <line x1="16" y1="-16" x2="-16" y2="16" stroke="#2a2418" strokeWidth="1.5"/>
        </g>
        <circle cx="57" cy="70" r="6" fill="#1a1610" stroke="#2e2820" strokeWidth="1"/>

        {/* Motor label */}
        <text x="57" y="138" textAnchor="middle" fill="#3a3020" fontSize="7" fontFamily="'IBM Plex Mono', monospace">MOTOR</text>
        <text x="57" y="147" textAnchor="middle" fill="#302a18" fontSize="7" fontFamily="'IBM Plex Mono', monospace">{compressor?.rpm || 0} RPM</text>

        {/* ── PRESSURE TANK (right) ── */}
        <rect x="120" y="15" width="108" height="110" rx="4" fill="#0f0d09" stroke="#2a2418" strokeWidth="1"/>
        <ellipse cx="174" cy="70" rx="42" ry="42" fill="#0a0907" stroke="#221e14" strokeWidth="1.5"/>
        <ellipse cx="174" cy="70" rx="32" ry="32" fill="none" stroke="#1e1a10" strokeWidth="1"/>
        {/* Pressure ring - fills based on pressure */}
        <ellipse cx="174" cy="70" rx="32" ry="32" fill="none"
          stroke={machColor} strokeWidth="3" opacity="0.3"
          strokeDasharray={`${((compressor?.pressure_bar || 8) / 10) * 201} 201`}/>
        <text x="174" y="66" textAnchor="middle" fill="#4a4030" fontSize="11" fontFamily="'IBM Plex Mono', monospace" fontWeight="600">
          {compressor?.pressure_bar || '--'}
        </text>
        <text x="174" y="78" textAnchor="middle" fill="#3a3020" fontSize="7" fontFamily="'IBM Plex Mono', monospace">bar</text>
        <text x="174" y="138" textAnchor="middle" fill="#3a3020" fontSize="7" fontFamily="'IBM Plex Mono', monospace">TANK</text>

        {/* ── COOLING FINS (bottom strip) ── */}
        <rect x="10" y="138" width="220" height="24" rx="2" fill="#0d0b08" stroke="#221e14" strokeWidth="1"/>
        {Array.from({ length: 18 }).map((_, i) => (
          <rect key={i} x={14 + i * 12} y="140" width="9" height="20" rx="1"
            fill={compState !== 'NORMAL' ? 'rgba(200,80,20,0.12)' : '#111009'}
            stroke="#1e1a10" strokeWidth="0.5"/>
        ))}
        <text x="120" y="153" textAnchor="middle" fill="#2a2418" fontSize="6" fontFamily="'IBM Plex Mono', monospace">COOLING</text>

        {/* ── STATUS PANEL (bottom) ── */}
        <rect x="10" y="172" width="220" height="38" rx="2" fill="#0d0b08" stroke="#221e14" strokeWidth="1"/>

        {/* State badge */}
        <rect x="14" y="177" width="80" height="18" rx="2" fill={machColor} opacity="0.15" stroke={machColor} strokeWidth="0.8" strokeOpacity="0.5"/>
        <text x="54" y="189" textAnchor="middle" fill={machColor} fontSize="8" fontFamily="'IBM Plex Mono', monospace" fontWeight="700">
          {compState}
        </text>

        {/* Temp display */}
        <text x="116" y="186" textAnchor="middle" fill="#4a4030" fontSize="10" fontFamily="'IBM Plex Mono', monospace">
          {compressor?.temp_c || '--'}°C
        </text>

        {/* Status LED */}
        <circle cx="188" cy="186" r="6" fill={machColor} opacity="0.9" filter="url(#fm-glow-sm)"
          style={{ animation: compState !== 'NORMAL' ? `df-pulse ${compState === 'FAILURE' ? '0.4' : compState === 'CRITICAL' ? '0.7' : '1.5'}s ease-in-out infinite` : 'none' }}/>
        <circle cx="188" cy="186" r="4" fill={machColor}/>

        {/* Click hint arrow */}
        <text x="205" y="189" fill="#3a3020" fontSize="12" fontFamily="sans-serif">›</text>

        {/* Label */}
        <text x="120" y="220" textAnchor="middle" fill="#4a3e24" fontSize="9" fontFamily="'IBM Plex Mono', monospace" letterSpacing="1">
          ESP32 #3 — COMPRESSOR
        </text>

        {/* Hover border overlay */}
        <rect x="0" y="0" width="240" height="220" rx="6"
          fill="none" stroke={machColor} strokeWidth="0" opacity="0.4"
          className="df-machine-hover-border"/>
      </g>

      {/* ── CABLE RUNS ── */}
      {/* Sensor → pipe */}
      <line x1="120" y1="237" x2="120" y2="64" stroke="#1a1610" strokeWidth="2" strokeDasharray="5,3"/>
      <line x1="120" y1="64" x2="350" y2="64" stroke="#1a1610" strokeWidth="2" strokeDasharray="5,3"/>
      {/* Actuator → pipe */}
      <line x1="204" y1="315" x2="204" y2="64" stroke="#1a1610" strokeWidth="1.5" strokeDasharray="5,3"/>
      {/* Compressor → east pipe */}
      <line x1="675" y1="210" x2="702" y2="210" stroke="#1a1610" strokeWidth="2" strokeDasharray="5,3"/>
      <line x1="702" y1="210" x2="702" y2="64" stroke="#1a1610" strokeWidth="2" strokeDasharray="5,3"/>
      <line x1="702" y1="64" x2="580" y2="64" stroke="#1a1610" strokeWidth="2" strokeDasharray="5,3"/>

      {/* ── DIMENSION / COMPASS ── */}
      <g transform="translate(680, 450)">
        <circle cx="0" cy="0" r="18" fill="#0f0d09" stroke="#2a2418" strokeWidth="1"/>
        <text x="0" y="-6" textAnchor="middle" fill="#2e2820" fontSize="7" fontFamily="'IBM Plex Mono', monospace">N</text>
        <line x1="0" y1="-13" x2="0" y2="-4" stroke="#3a3020" strokeWidth="1.5"/>
        <line x1="0" y1="4" x2="0" y2="13" stroke="#2a2418" strokeWidth="1"/>
        <line x1="-13" y1="0" x2="13" y2="0" stroke="#2a2418" strokeWidth="0.8"/>
        <circle cx="0" cy="0" r="2" fill="#2e2820"/>
      </g>

      {/* Scale bar */}
      <g transform="translate(560, 460)">
        <line x1="0" y1="0" x2="80" y2="0" stroke="#2a2418" strokeWidth="1.5"/>
        <line x1="0" y1="-4" x2="0" y2="4" stroke="#2a2418" strokeWidth="1.5"/>
        <line x1="80" y1="-4" x2="80" y2="4" stroke="#2a2418" strokeWidth="1.5"/>
        <text x="40" y="-7" textAnchor="middle" fill="#2a2418" fontSize="7" fontFamily="'IBM Plex Mono', monospace">4 m</text>
      </g>

      {/* Node index labels */}
      <text x="42" y="478" fill="#252018" fontSize="8" fontFamily="'IBM Plex Mono', monospace">DARK FACTORY — FLOOR PLAN v1.0</text>
    </svg>
  );
}

Object.assign(window, { FloorMap });
