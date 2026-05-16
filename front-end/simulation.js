// Dark Factory — Simulation Engine
// Exports: window.DFSim
(function () {
  'use strict';

  const STATES = ['NORMAL', 'HEATING', 'DEGRADING', 'CRITICAL', 'FAILURE'];

  const STATE_COLORS = {
    NORMAL:    '#3ecf6e',
    HEATING:   '#f0a020',
    DEGRADING: '#e06820',
    CRITICAL:  '#f04040',
    FAILURE:   '#cc1818'
  };

  const ALARM_COLORS = {
    OK:       '#3ecf6e',
    WARNING:  '#f0b030',
    CRITICAL: '#f04040'
  };

  const RANGES = {
    NORMAL:    { temp:[33,45],   rpm:[1420,1480], vib:[0.15,0.40], press:[7.5,8.5], oilTemp:[38,45],  airflow:[260,290], power:[720,780]  },
    HEATING:   { temp:[45,70],   rpm:[1380,1460], vib:[0.30,0.65], press:[7.0,8.5], oilTemp:[45,65],  airflow:[240,270], power:[760,820]  },
    DEGRADING: { temp:[70,88],   rpm:[1300,1420], vib:[0.50,1.50], press:[5.5,7.5], oilTemp:[65,82],  airflow:[200,245], power:[680,760]  },
    CRITICAL:  { temp:[88,105],  rpm:[1100,1300], vib:[1.50,3.50], press:[3.0,5.5], oilTemp:[82,98],  airflow:[140,200], power:[620,680]  },
    FAILURE:   { temp:[100,115], rpm:[0,1100],    vib:[3.50,8.00], press:[0.0,3.0], oilTemp:[98,112], airflow:[0,140],   power:[400,620]  }
  };

  function rnd(a, b) { return a + Math.random() * (b - a); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, a, b) { return Math.min(Math.max(v, a), b); }
  function f1(v) { return +v.toFixed(1); }
  function f2(v) { return +v.toFixed(2); }

  function snapshot(state) {
    const g = RANGES[state];
    return {
      state,
      temp_c:       f1(rnd(...g.temp)),
      rpm:          Math.round(rnd(...g.rpm)),
      vibration_g:  f2(rnd(...g.vib)),
      pressure_bar: f2(rnd(...g.press)),
      oil_temp_c:   f1(rnd(...g.oilTemp)),
      airflow_lpm:  Math.round(rnd(...g.airflow)),
      power_w:      Math.round(rnd(...g.power)),
    };
  }

  function createSim() {
    const MAX_HIST = 40;
    let stateIdx = 0;
    let ticker = 0;
    const TICKS_PER_STATE = 18;
    let autoAdv = true;
    let current = snapshot('NORMAL');

    const histKeys = ['temp_c','rpm','vibration_g','pressure_bar','oil_temp_c','airflow_lpm','power_w'];
    const history = {};
    histKeys.forEach(k => { history[k] = Array(8).fill(current[k]); });

    let prevSensor = {
      temp_c: 24.5, humidity_pct: 58.2, pressure_hpa: 1013.1,
      co2_ppm: 420, lpg_ppm: 115, alarm: 'OK'
    };

    function tick() {
      ticker++;
      if (autoAdv && ticker % TICKS_PER_STATE === 0) {
        stateIdx = (stateIdx + 1) % STATES.length;
      }
      const state = STATES[stateIdx];
      const tgt = snapshot(state);
      const g = RANGES[state];
      const a = 0.24;

      current = {
        state,
        temp_c:       f1(clamp(lerp(current.temp_c, tgt.temp_c, a), g.temp[0], g.temp[1])),
        rpm:          Math.round(clamp(lerp(current.rpm, tgt.rpm, a), g.rpm[0], g.rpm[1])),
        vibration_g:  f2(clamp(lerp(current.vibration_g, tgt.vibration_g, a), g.vib[0], g.vib[1])),
        pressure_bar: f2(clamp(lerp(current.pressure_bar, tgt.pressure_bar, a), g.press[0], g.press[1])),
        oil_temp_c:   f1(clamp(lerp(current.oil_temp_c, tgt.oil_temp_c, a), g.oilTemp[0], g.oilTemp[1])),
        airflow_lpm:  Math.round(clamp(lerp(current.airflow_lpm, tgt.airflow_lpm, a), g.airflow[0], g.airflow[1])),
        power_w:      Math.round(clamp(lerp(current.power_w, tgt.power_w, a), g.power[0], g.power[1])),
      };

      histKeys.forEach(k => {
        history[k].push(current[k]);
        if (history[k].length > MAX_HIST) history[k].shift();
      });

      return { current: { ...current }, history: Object.fromEntries(histKeys.map(k => [k, [...history[k]]])) };
    }

    function tickSensor() {
      const hf = stateIdx;
      const co2Target  = clamp(400 + hf * 130 + rnd(-50, 50), 350, 2200);
      const lpgTarget  = clamp(90  + hf *  42 + rnd(-25, 25), 70,  650);
      const tempTarget = f1(22 + hf * 1.9 + rnd(-1.2, 1.2));
      const humTarget  = f1(clamp(62 - hf * 5 + rnd(-4, 4), 18, 85));
      const pressTarget = f1(1013 + rnd(-2.5, 2.5));

      const sa = 0.18;
      const co2  = Math.round(lerp(prevSensor.co2_ppm, co2Target, sa));
      const lpg  = Math.round(lerp(prevSensor.lpg_ppm, lpgTarget, sa));
      const temp = f1(lerp(prevSensor.temp_c, tempTarget, sa));
      const hum  = f1(lerp(prevSensor.humidity_pct, humTarget, sa));
      const press = f1(lerp(prevSensor.pressure_hpa, pressTarget, sa));

      let alarm = 'OK';
      if (co2 > 800 || lpg > 300) alarm = 'WARNING';
      if (co2 > 1500 || lpg > 500) alarm = 'CRITICAL';

      prevSensor = { temp_c: temp, humidity_pct: hum, pressure_hpa: press, co2_ppm: co2, lpg_ppm: lpg, alarm };
      return { ...prevSensor };
    }

    function forceState(s) {
      const idx = STATES.indexOf(s);
      if (idx >= 0) { stateIdx = idx; ticker = 0; }
    }
    function setAuto(v) { autoAdv = v; }
    function getStateIndex() { return stateIdx; }

    return { tick, tickSensor, forceState, setAuto, getStateIndex };
  }

  function initActuator() {
    return { fan_pct: 0, sg90_angle: 0, as100_angle: 0, buzzer: false, buzzer_freq: 1000, led: false, mist: false };
  }

  function applyCmd(actuator, cmd) {
    const s = { ...actuator };
    switch (cmd.cmd) {
      case 'fan':         s.fan_pct      = clamp(+cmd.value, 0, 100); break;
      case 'servo_sg90':  s.sg90_angle   = clamp(+cmd.angle, 0, 180); break;
      case 'servo_as100': s.as100_angle  = clamp(+cmd.angle, 0, 180); break;
      case 'buzzer':      s.buzzer       = !!cmd.state; if (cmd.freq) s.buzzer_freq = +cmd.freq; break;
      case 'led':         s.led          = !!cmd.state; break;
      case 'mist':        s.mist         = !!cmd.state; break;
      case 'reset':       return initActuator();
    }
    return s;
  }

  window.DFSim = { STATES, STATE_COLORS, ALARM_COLORS, RANGES, createSim, initActuator, applyCmd };
})();
