// MachineDetail.jsx — Machine detail page
// Requires: window.DFSim

// ── Sparkline ────────────────────────────────────────────
function Sparkline({ data, color, width, height }) {
  const w = width || 130, h = height || 38;
  if (!data || data.length < 2) return <svg width={w} height={h}></svg>;
  const min = Math.min(...data), max = Math.max(...data);
  const range = (max - min) || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - 4 - ((v - min) / range) * (h - 8);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const fillPts = `0,${h} ` + pts + ` ${w},${h}`;
  return (
    <svg width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
      <defs>
        <linearGradient id={`spk-grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polygon points={fillPts} fill={`url(#spk-grad-${color.replace('#','')})`}/>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
      {/* Last point dot */}
      {data.length > 0 && (() => {
        const lastX = w;
        const lastY = h - 4 - ((data[data.length - 1] - min) / range) * (h - 8);
        return <circle cx={lastX} cy={lastY} r="2.5" fill={color}/>;
      })()}
    </svg>
  );
}

// ── MetricCard ───────────────────────────────────────────
function MetricCard({ label, value, unit, history, color, subtext }) {
  const c = color || '#d4870a';
  return (
    <div style={{
      background: '#14120d',
      border: '1px solid #2a2418',
      borderRadius: '6px',
      padding: '12px 14px 10px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      minWidth: 0,
    }}>
      <div style={{ color: '#5a5040', fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '1px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
        <span style={{ color: c, fontSize: '22px', fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, lineHeight: 1 }}>
          {value}
        </span>
        <span style={{ color: '#4a4030', fontSize: '11px', fontFamily: "'IBM Plex Mono', monospace" }}>{unit}</span>
      </div>
      {subtext && (
        <div style={{ color: '#3a3020', fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace" }}>{subtext}</div>
      )}
      <Sparkline data={history} color={c} width={130} height={32}/>
    </div>
  );
}

// ── ServoGauge ───────────────────────────────────────────
function ServoGauge({ angle, maxAngle, color, size }) {
  const s = size || 56;
  const r = s / 2 - 6;
  const cx = s / 2, cy = s / 2;
  const startRad = Math.PI * 0.75;
  const sweepRad = Math.PI * 1.5;
  const toXY = (rad, radius) => ({
    x: cx + Math.cos(rad) * radius,
    y: cy + Math.sin(rad) * radius
  });
  const arcPath = (r, startA, endA) => {
    const s = toXY(startA, r), e = toXY(endA, r);
    const large = (endA - startA) > Math.PI ? 1 : 0;
    return `M ${s.x.toFixed(2)},${s.y.toFixed(2)} A ${r},${r} 0 ${large} 1 ${e.x.toFixed(2)},${e.y.toFixed(2)}`;
  };
  const normAngle = (angle / (maxAngle || 180));
  const endRad = startRad + sweepRad * normAngle;
  const needle = toXY(endRad, r - 4);
  return (
    <svg width={s} height={s} style={{ display: 'block' }}>
      {/* Track */}
      <path d={arcPath(r, startRad, startRad + sweepRad)} fill="none" stroke="#2a2418" strokeWidth="4" strokeLinecap="round"/>
      {/* Value arc */}
      {normAngle > 0.01 && (
        <path d={arcPath(r, startRad, endRad)} fill="none" stroke={color || '#d4870a'} strokeWidth="4" strokeLinecap="round"/>
      )}
      {/* Needle */}
      <line x1={cx.toFixed(1)} y1={cy.toFixed(1)} x2={needle.x.toFixed(1)} y2={needle.y.toFixed(1)}
        stroke={color || '#d4870a'} strokeWidth="2" strokeLinecap="round"/>
      <circle cx={cx} cy={cy} r="3" fill="#1a1610" stroke="#3a3020" strokeWidth="1"/>
    </svg>
  );
}

// ── FanArc ───────────────────────────────────────────────
function FanDisplay({ pct, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div style={{
        width: '36px', height: '36px', borderRadius: '50%',
        border: `2px solid #2a2418`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#0f0d09', position: 'relative', overflow: 'hidden'
      }}>
        <div style={{
          width: '26px', height: '26px',
          background: `conic-gradient(${color || '#d4870a'} ${pct * 3.6}deg, #1a1610 ${pct * 3.6}deg)`,
          borderRadius: '50%',
          animation: pct > 0 ? `df-spin ${Math.max(0.15, 1.2 - pct * 0.01)}s linear infinite` : 'none'
        }}></div>
        <div style={{
          position: 'absolute', width: '12px', height: '12px',
          background: '#0f0d09', borderRadius: '50%', border: '1px solid #2a2418'
        }}></div>
      </div>
    </div>
  );
}

// ── Toggle ───────────────────────────────────────────────
function Toggle({ value, onChange, color }) {
  return (
    <div
      onClick={() => onChange(!value)}
      style={{
        width: '44px', height: '24px', borderRadius: '12px',
        background: value ? (color || '#d4870a') : '#1a1610',
        border: `1px solid ${value ? (color || '#d4870a') : '#2a2418'}`,
        cursor: 'pointer', position: 'relative', transition: 'all 0.2s',
        flexShrink: 0,
      }}
    >
      <div style={{
        position: 'absolute', top: '3px',
        left: value ? '22px' : '3px',
        width: '16px', height: '16px', borderRadius: '50%',
        background: value ? '#fff' : '#3a3020',
        transition: 'left 0.2s', boxShadow: value ? `0 0 6px ${color || '#d4870a'}` : 'none'
      }}></div>
    </div>
  );
}

// ── StateMachine ─────────────────────────────────────────
function StateMachine({ currentState, onForceState, liveMode }) {
  const { STATES, STATE_COLORS } = window.DFSim;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0', overflowX: 'auto', padding: '4px 0 8px' }}>
      {STATES.map((s, i) => {
        const active = s === currentState;
        const past   = STATES.indexOf(currentState) > i;
        const col    = STATE_COLORS[s];
        return (
          <React.Fragment key={s}>
            <div
              onClick={() => !liveMode && onForceState(s)}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
                cursor: liveMode ? 'default' : 'pointer',
                flexShrink: 0,
              }}
            >
              <div style={{
                padding: '7px 14px', borderRadius: '4px', fontSize: '10px',
                fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, letterSpacing: '0.8px',
                background: active ? col + '22' : past ? col + '0a' : '#14120d',
                border: `1.5px solid ${active ? col : past ? col + '44' : '#2a2418'}`,
                color: active ? col : past ? col + 'aa' : '#4a4030',
                boxShadow: active ? `0 0 12px ${col}44` : 'none',
                transition: 'all 0.4s',
                animation: active && currentState === 'FAILURE' ? 'df-pulse 0.6s ease-in-out infinite' : 'none',
                whiteSpace: 'nowrap',
              }}>
                {s}
              </div>
              {active && (
                <div style={{ width: '4px', height: '4px', borderRadius: '50%', background: col }}></div>
              )}
            </div>
            {i < STATES.length - 1 && (
              <div style={{ color: '#2a2418', fontSize: '16px', margin: '0 2px', flexShrink: 0, paddingBottom: active || STATES.indexOf(currentState) > i ? '16px' : '4px' }}>›</div>
            )}
          </React.Fragment>
        );
      })}
      {!liveMode && (
        <div style={{ marginLeft: '16px', color: '#4a4030', fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace", flexShrink: 0 }}>
          click to force state
        </div>
      )}
    </div>
  );
}

// ── MachineDetail ─────────────────────────────────────────
function MachineDetail({ compressor, history, actuator, onActuatorCmd, onBack, liveMode, onToggleLive, onForceState }) {
  const { STATE_COLORS } = window.DFSim;
  const state     = (compressor && compressor.state) || 'NORMAL';
  const col       = STATE_COLORS[state] || '#d4870a';
  const amber     = '#d4870a';

  const metricColor = (key) => {
    const dangerKeys = ['temp_c', 'vibration_g'];
    const warnKeys   = ['rpm', 'pressure_bar'];
    if (dangerKeys.includes(key)) return col;
    if (warnKeys.includes(key))   return amber;
    return '#8a7060';
  };

  const metrics = [
    { key: 'temp_c',       label: 'Temperature', value: compressor?.temp_c,       unit: '°C',  sub: `oil: ${compressor?.oil_temp_c}°C` },
    { key: 'rpm',          label: 'RPM',          value: compressor?.rpm,           unit: 'rpm', sub: 'motor speed' },
    { key: 'vibration_g',  label: 'Vibration',    value: compressor?.vibration_g,   unit: 'g',   sub: 'accel RMS' },
    { key: 'pressure_bar', label: 'Pressure',     value: compressor?.pressure_bar,  unit: 'bar', sub: 'output' },
    { key: 'oil_temp_c',   label: 'Oil Temp',     value: compressor?.oil_temp_c,    unit: '°C',  sub: 'lubrication' },
    { key: 'airflow_lpm',  label: 'Airflow',      value: compressor?.airflow_lpm,   unit: 'lpm', sub: 'compressor output' },
    { key: 'power_w',      label: 'Power',        value: compressor?.power_w,       unit: 'W',   sub: 'consumption' },
  ];

  // Local slider state
  const [fanVal,      setFanVal]      = React.useState(actuator?.fan_pct      || 0);
  const [sg90Val,     setSg90Val]     = React.useState(actuator?.sg90_angle   || 0);
  const [as100Val,    setAs100Val]    = React.useState(actuator?.as100_angle  || 0);
  const [buzzerFreq,  setBuzzerFreq]  = React.useState(actuator?.buzzer_freq  || 1000);

  // Keep sliders in sync when actuator changes externally
  React.useEffect(() => { setFanVal(actuator?.fan_pct      || 0); }, [actuator?.fan_pct]);
  React.useEffect(() => { setSg90Val(actuator?.sg90_angle  || 0); }, [actuator?.sg90_angle]);
  React.useEffect(() => { setAs100Val(actuator?.as100_angle|| 0); }, [actuator?.as100_angle]);

  const sendFan    = (v) => { setFanVal(v);    onActuatorCmd({ cmd: 'fan',         value: v }); };
  const sendSg90   = (v) => { setSg90Val(v);   onActuatorCmd({ cmd: 'servo_sg90',  angle: v }); };
  const sendAs100  = (v) => { setAs100Val(v);  onActuatorCmd({ cmd: 'servo_as100', angle: v }); };
  const sendBuzzer = (on) => onActuatorCmd({ cmd: 'buzzer', state: on ? 1 : 0, freq: buzzerFreq });
  const sendFreq   = (f) => { setBuzzerFreq(f); if (actuator?.buzzer) onActuatorCmd({ cmd: 'buzzer', state: 1, freq: f }); };
  const sendLed    = (on) => onActuatorCmd({ cmd: 'led',  state: on ? 1 : 0 });
  const sendMist   = (on) => onActuatorCmd({ cmd: 'mist', state: on ? 1 : 0 });
  const sendReset  = ()   => onActuatorCmd({ cmd: 'reset' });

  const sliderStyle = (val, max, color) => ({
    WebkitAppearance: 'none', appearance: 'none',
    width: '100%', height: '4px', borderRadius: '2px', outline: 'none', cursor: 'pointer',
    background: `linear-gradient(to right, ${color} 0%, ${color} ${(val/max)*100}%, #2a2418 ${(val/max)*100}%, #2a2418 100%)`,
  });

  const rowStyle = {
    display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px',
    borderBottom: '1px solid #1e1a14',
  };
  const labelStyle = {
    color: '#5a5040', fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace",
    letterSpacing: '0.8px', textTransform: 'uppercase', width: '80px', flexShrink: 0,
  };
  const valStyle = {
    color: amber, fontSize: '13px', fontFamily: "'IBM Plex Mono', monospace",
    fontWeight: 700, width: '52px', textAlign: 'right', flexShrink: 0,
  };

  return (
    <div style={{
      height: '100vh', background: '#0d0b09', color: '#e8ddd0',
      fontFamily: "'IBM Plex Sans', sans-serif", display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* ── HEADER ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '16px', padding: '14px 24px',
        borderBottom: '1px solid #1e1a14', background: '#0f0d09', flexShrink: 0,
      }}>
        <button
          onClick={onBack}
          style={{
            background: 'none', border: '1px solid #2a2418', borderRadius: '4px',
            color: '#8a7060', padding: '6px 12px', cursor: 'pointer', fontSize: '12px',
            fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', gap: '6px',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#4a3e24'; e.currentTarget.style.color = '#e8ddd0'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2418'; e.currentTarget.style.color = '#8a7060'; }}
        >
          ‹ FLOOR
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: col,
            boxShadow: `0 0 8px ${col}`, animation: state !== 'NORMAL' ? 'df-pulse 1s ease-in-out infinite' : 'none' }}></div>
          <span style={{ fontSize: '13px', fontFamily: "'IBM Plex Mono', monospace", color: '#8a7060', letterSpacing: '2px' }}>
            COMPRESSOR
          </span>
        </div>

        <div style={{
          padding: '4px 12px', borderRadius: '3px', fontSize: '10px',
          fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, letterSpacing: '1px',
          background: col + '1a', border: `1px solid ${col}66`, color: col,
        }}>
          {state}
        </div>

        <div style={{ flex: 1 }}></div>

        {/* Live/Demo toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace", color: '#4a4030' }}>DEMO</span>
          <Toggle value={liveMode} onChange={onToggleLive} color="#d4870a"/>
          <span style={{ fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace", color: liveMode ? '#d4870a' : '#4a4030' }}>LIVE</span>
          {liveMode && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#d4870a', animation: 'df-pulse 1s ease-in-out infinite' }}></div>}
        </div>
      </div>

      {/* ── BODY ── */}
      <div style={{ flex: 1, overflow: 'auto', padding: '0' }}>

        {/* State machine section */}
        <div style={{ padding: '16px 24px 12px', borderBottom: '1px solid #1a1710' }}>
          <div style={{ fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace", color: '#3a3020', letterSpacing: '2px', marginBottom: '12px' }}>
            STATE MACHINE — ESP32 #3
          </div>
          <StateMachine currentState={state} onForceState={onForceState} liveMode={liveMode}/>
        </div>

        {/* Metrics grid */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid #1a1710' }}>
          <div style={{ fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace", color: '#3a3020', letterSpacing: '2px', marginBottom: '12px' }}>
            TELEMETRY — ESP32 #3
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '8px',
          }}>
            {metrics.map(m => (
              <MetricCard
                key={m.key}
                label={m.label}
                value={m.value ?? '—'}
                unit={m.unit}
                history={history?.[m.key] || []}
                color={metricColor(m.key)}
                subtext={m.sub}
              />
            ))}
          </div>
        </div>

        {/* Actuator controls */}
        <div style={{ padding: '16px 0 24px' }}>
          <div style={{ fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace", color: '#3a3020', letterSpacing: '2px', marginBottom: '4px', padding: '0 24px' }}>
            ACTUATOR CONTROLS — ESP32 #2
          </div>

          {/* FAN */}
          <div style={rowStyle}>
            <div style={labelStyle}>FAN</div>
            <FanDisplay pct={fanVal} color="#d4870a"/>
            <div style={{ flex: 1 }}>
              <input type="range" min="0" max="100" value={fanVal}
                onChange={e => sendFan(+e.target.value)}
                style={sliderStyle(fanVal, 100, '#d4870a')}/>
            </div>
            <div style={valStyle}>{fanVal}%</div>
          </div>

          {/* SERVO SG90 */}
          <div style={rowStyle}>
            <div style={labelStyle}>SG90</div>
            <ServoGauge angle={sg90Val} maxAngle={180} color="#d4870a" size={52}/>
            <div style={{ flex: 1 }}>
              <input type="range" min="0" max="180" value={sg90Val}
                onChange={e => sendSg90(+e.target.value)}
                style={sliderStyle(sg90Val, 180, '#d4870a')}/>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                <span style={{ color: '#3a3020', fontSize: '8px', fontFamily: "'IBM Plex Mono', monospace" }}>0° closed</span>
                <span style={{ color: '#3a3020', fontSize: '8px', fontFamily: "'IBM Plex Mono', monospace" }}>90° half</span>
                <span style={{ color: '#3a3020', fontSize: '8px', fontFamily: "'IBM Plex Mono', monospace" }}>180° open</span>
              </div>
            </div>
            <div style={valStyle}>{sg90Val}°</div>
          </div>

          {/* SERVO AS100 */}
          <div style={rowStyle}>
            <div style={labelStyle}>AS100</div>
            <ServoGauge angle={as100Val} maxAngle={180} color="#8a7060" size={52}/>
            <div style={{ flex: 1 }}>
              <input type="range" min="0" max="180" value={as100Val}
                onChange={e => sendAs100(+e.target.value)}
                style={sliderStyle(as100Val, 180, '#8a7060')}/>
            </div>
            <div style={{ ...valStyle, color: '#8a7060' }}>{as100Val}°</div>
          </div>

          {/* BUZZER */}
          <div style={rowStyle}>
            <div style={labelStyle}>BUZZER</div>
            <Toggle value={actuator?.buzzer || false} onChange={sendBuzzer} color="#f07030"/>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#4a4030', fontSize: '9px', fontFamily: "'IBM Plex Mono', monospace", width: '30px' }}>FREQ</span>
                <input type="range" min="200" max="4000" step="100" value={buzzerFreq}
                  onChange={e => sendFreq(+e.target.value)}
                  style={{ ...sliderStyle(buzzerFreq - 200, 3800, actuator?.buzzer ? '#f07030' : '#4a4030'), flex: 1 }}/>
                <span style={{ color: actuator?.buzzer ? '#f07030' : '#4a4030', fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace", width: '56px', textAlign: 'right' }}>{buzzerFreq} Hz</span>
              </div>
            </div>
            {actuator?.buzzer && (
              <div style={{ color: '#f07030', fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace',", animation: 'df-pulse 0.5s ease-in-out infinite' }}>
                ◈ ON
              </div>
            )}
          </div>

          {/* LED + MIST */}
          <div style={{ ...rowStyle, borderBottom: 'none' }}>
            <div style={labelStyle}>LED</div>
            <Toggle value={actuator?.led || false} onChange={sendLed} color="#f0e060"/>
            <div style={{
              width: '24px', height: '24px', borderRadius: '50%',
              background: actuator?.led ? '#f0e060' : '#1a1610',
              border: '1px solid #2a2418',
              boxShadow: actuator?.led ? '0 0 12px #f0e06088' : 'none',
              transition: 'all 0.2s', flexShrink: 0,
            }}></div>

            <div style={{ width: '40px' }}></div>

            <div style={labelStyle}>MIST</div>
            <Toggle value={actuator?.mist || false} onChange={sendMist} color="#40a0f0"/>
            {actuator?.mist && (
              <div style={{ color: '#40a0f0', fontSize: '10px', fontFamily: "'IBM Plex Mono', monospace", animation: 'df-pulse 1.2s ease-in-out infinite' }}>
                ≈ ACTIVE
              </div>
            )}

            <div style={{ flex: 1 }}></div>

            <button
              onClick={sendReset}
              style={{
                background: '#14120d', border: '1px solid #2a2418', borderRadius: '4px',
                color: '#6a5040', padding: '6px 14px', cursor: 'pointer', fontSize: '10px',
                fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.5px',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#c83020'; e.currentTarget.style.color = '#f05030'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2418'; e.currentTarget.style.color = '#6a5040'; }}
            >
              RESET ALL
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

Object.assign(window, { MachineDetail });
