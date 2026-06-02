#!/usr/bin/env python3
"""
Dark Factory — Hardware Simulation Script
==========================================
Simulates ESP32 sensor nodes and Raspberry Pi LLM decisions,
pumping realistic data into the MOD-05 API for end-to-end testing.

Run:
    python3 simulate.py              # default: http://localhost:8000
    python3 simulate.py --url http://192.168.1.50:8000

Requires: httpx  (already in requirements.txt)
"""

import asyncio
import argparse
import random
import time
import math
import sys

import httpx

# ── Configuration ────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"

AMBIENT_INTERVAL   = 3.0   # seconds
MACHINE_INTERVAL   = 1.0
REPORT_INTERVAL    = 60.0
ALARM_INTERVAL_MIN = 30.0
ALARM_INTERVAL_MAX = 40.0

STATE_TICKS        = 18    # machine ticks per state before advancing
LERP_ALPHA         = 0.24  # smoothing factor for value transitions

# ── ANSI Colors ──────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    BG_RED  = "\033[41m"


# ── State Machine ────────────────────────────────────────────

STATES = ["NORMAL", "HEATING", "DEGRADING", "CRITICAL", "FAILURE"]

RANGES = {
    "NORMAL":    {"temp": (33, 45),   "rpm": (1420, 1480), "vib": (0.15, 0.40), "pressure": (7.5, 8.5),  "oil_temp": (38, 45),  "airflow": (260, 290), "power": (720, 780)},
    "HEATING":   {"temp": (45, 70),   "rpm": (1380, 1460), "vib": (0.30, 0.65), "pressure": (7.0, 8.5),  "oil_temp": (45, 65),  "airflow": (240, 270), "power": (760, 820)},
    "DEGRADING": {"temp": (70, 88),   "rpm": (1300, 1420), "vib": (0.50, 1.50), "pressure": (5.5, 7.5),  "oil_temp": (65, 82),  "airflow": (200, 245), "power": (680, 760)},
    "CRITICAL":  {"temp": (88, 105),  "rpm": (1100, 1300), "vib": (1.50, 3.50), "pressure": (3.0, 5.5),  "oil_temp": (82, 98),  "airflow": (140, 200), "power": (620, 680)},
    "FAILURE":   {"temp": (100, 115), "rpm": (0, 1100),    "vib": (3.50, 8.00), "pressure": (0.0, 3.0),  "oil_temp": (98, 112), "airflow": (0, 140),   "power": (400, 620)},
}

RISK_MAP = {
    "NORMAL":    "RISK_OK",
    "HEATING":   "RISK_WATCH",
    "DEGRADING": "RISK_WARN",
    "CRITICAL":  "RISK_CRITICAL",
    "FAILURE":   "RISK_CRITICAL",
}

FAILURE_HRS_MAP = {
    "NORMAL":    99.0,
    "HEATING":   18.0,
    "DEGRADING": 6.0,
    "CRITICAL":  1.5,
    "FAILURE":   0.0,
}

ANOMALY_MAP = {
    "NORMAL":    [],
    "HEATING":   ["machine_temp_rising"],
    "DEGRADING": ["machine_temp_rising", "rpm_dropping"],
    "CRITICAL":  ["machine_temp_rising", "rpm_dropping", "vibration_spike"],
    "FAILURE":   ["machine_temp_critical", "rpm_critical", "vibration_critical", "pressure_drop"],
}

ACTION_MAP = {
    "NORMAL":    "No action required.",
    "HEATING":   "Monitor closely. Consider activating zone cooling.",
    "DEGRADING": "activate_zone_a_cooling",
    "CRITICAL":  "Immediate shutdown recommended. Inspect bearings and coolant.",
    "FAILURE":   "EMERGENCY: Machine has failed. Initiate emergency shutdown protocol.",
}


# ── Ambient zone profiles ────────────────────────────────────

AMBIENT_PROFILES = {
    "ZONE_A": {
        "temp_base": 26.0, "temp_var": 4.0,
        "hum_base":  55.0, "hum_var":  8.0,
        "co2_base":  400.0, "co2_var":  50.0,
        "pm25_base": 10.0, "pm25_var": 5.0,
        "lpg_base":  110.0, "lpg_var": 20.0,
        "pres_base": 1013.0, "pres_var": 2.0,
    },
    "ZONE_B": {
        "temp_base": 24.0, "temp_var": 3.5,
        "hum_base":  52.0, "hum_var":  6.0,
        "co2_base":  380.0, "co2_var":  40.0,
        "pm25_base": 8.0,  "pm25_var": 4.0,
        "lpg_base":  100.0, "lpg_var": 15.0,
        "pres_base": 1013.0, "pres_var": 2.0,
    },
}

# Alarm thresholds for ambient sensors
ALARM_THRESHOLDS = {
    "temperature_c": 40.0,
    "co2_ppm":       1000.0,
    "pm25":          35.0,
    "humidity_pct":  80.0,
}


# ── Helpers ──────────────────────────────────────────────────

def ts_now() -> int:
    return int(time.time() * 1000)


def clock() -> str:
    return time.strftime("%H:%M:%S")


def lerp(current: float, target: float, alpha: float) -> float:
    return current + alpha * (target - current)


def rand_in(lo: float, hi: float) -> float:
    return random.uniform(lo, hi)


def rnd(v: float, n: int = 1) -> float:
    return round(v, n)


def color_for_state(state: str) -> str:
    if state in ("NORMAL",):
        return C.GREEN
    elif state in ("HEATING",):
        return C.YELLOW
    elif state in ("DEGRADING",):
        return C.YELLOW + C.BOLD
    elif state in ("CRITICAL",):
        return C.RED
    else:
        return C.BG_RED + C.WHITE + C.BOLD


def risk_color(risk: str) -> str:
    if risk == "RISK_OK":
        return C.GREEN
    elif risk == "RISK_WATCH":
        return C.YELLOW
    elif risk == "RISK_WARN":
        return C.YELLOW + C.BOLD
    else:
        return C.RED + C.BOLD


# ── Machine State Manager ───────────────────────────────────

class MachineState:
    def __init__(self):
        self.state_idx = 0
        self.tick = 0
        # Current smoothed values (start at mid-range of NORMAL)
        r = RANGES["NORMAL"]
        self.temp     = (r["temp"][0] + r["temp"][1]) / 2
        self._rpm     = (r["rpm"][0] + r["rpm"][1]) / 2
        self.vib      = (r["vib"][0] + r["vib"][1]) / 2
        self.pressure = (r["pressure"][0] + r["pressure"][1]) / 2
        self.oil_temp = (r["oil_temp"][0] + r["oil_temp"][1]) / 2
        self.airflow  = (r["airflow"][0] + r["airflow"][1]) / 2
        self.power    = (r["power"][0] + r["power"][1]) / 2

    @property
    def state(self) -> str:
        return STATES[self.state_idx]

    @property
    def risk(self) -> str:
        return RISK_MAP[self.state]

    def advance_tick(self):
        self.tick += 1
        if self.tick >= STATE_TICKS:
            self.tick = 0
            self.state_idx = (self.state_idx + 1) % len(STATES)
            sc = color_for_state(self.state)
            print(f"{C.BOLD}{C.MAGENTA}[{clock()}] [STATE]    ═══ Transitioned to {sc}{self.state}{C.RESET}{C.BOLD}{C.MAGENTA} ═══{C.RESET}")

    @property
    def temp_c(self) -> float:     return rnd(self.temp, 1)
    @property
    def rpm(self) -> float:        return rnd(self._rpm, 1)
    @property
    def vibration_g(self) -> float: return rnd(self.vib, 2)
    @property
    def pressure_bar(self) -> float: return rnd(self.pressure, 2)
    @property
    def oil_temp_c(self) -> float:  return rnd(self.oil_temp, 1)
    @property
    def airflow_lpm(self) -> float: return rnd(self.airflow, 1)
    @property
    def power_w(self) -> float:    return rnd(self.power, 1)

    def update(self):
        """Lerp all values toward the current state's range."""
        r = RANGES[self.state]

        # Pick random targets within the current state's range
        t_temp     = rand_in(*r["temp"])
        t_rpm      = rand_in(*r["rpm"])
        t_vib      = rand_in(*r["vib"])
        t_pressure = rand_in(*r["pressure"])
        t_oil      = rand_in(*r["oil_temp"])
        t_airflow  = rand_in(*r["airflow"])
        t_power    = rand_in(*r["power"])

        # Smooth lerp
        self.temp     = lerp(self.temp,     t_temp,     LERP_ALPHA)
        self._rpm     = lerp(self._rpm,     t_rpm,      LERP_ALPHA)
        self.vib      = lerp(self.vib,      t_vib,      LERP_ALPHA)
        self.pressure = lerp(self.pressure, t_pressure, LERP_ALPHA)
        self.oil_temp = lerp(self.oil_temp, t_oil,      LERP_ALPHA)
        self.airflow  = lerp(self.airflow,  t_airflow,  LERP_ALPHA)
        self.power    = lerp(self.power,    t_power,    LERP_ALPHA)

        self.advance_tick()


# ── Ambient Generator ────────────────────────────────────────

class AmbientGenerator:
    """Generates slowly drifting ambient sensor values with sinusoidal variation."""
    def __init__(self):
        self.t = 0  # time counter for sin-based drift

    def generate(self, zone_id: str) -> dict:
        self.t += 1
        p = AMBIENT_PROFILES[zone_id]

        # Sinusoidal drift + small random noise
        phase = self.t * 0.05 + (0 if zone_id == "ZONE_A" else math.pi / 3)
        drift = math.sin(phase) * 0.5

        temp = p["temp_base"] + drift * p["temp_var"] / 2 + random.gauss(0, 0.3)
        hum  = p["hum_base"]  - drift * p["hum_var"] / 3 + random.gauss(0, 0.5)
        co2  = p["co2_base"]  + abs(drift) * p["co2_var"] + random.gauss(0, 5)
        pm25 = p["pm25_base"] + abs(drift) * p["pm25_var"] / 2 + random.gauss(0, 0.5)
        lpg  = p["lpg_base"]  + abs(drift) * p["lpg_var"]       + random.gauss(0, 3)
        pres = p["pres_base"] + drift * p["pres_var"] / 2       + random.gauss(0, 0.2)

        return {
            "zone_id":       zone_id,
            "temperature_c": rnd(max(15, temp), 1),
            "humidity_pct":  rnd(max(20, min(95, hum)), 1),
            "co2_ppm":       rnd(max(300, co2), 1),
            "pm25":          rnd(max(1, pm25), 1),
            "lpg_ppm":       rnd(max(0, lpg), 1),
            "pressure_hpa":  rnd(max(950, pres), 1),
            "timestamp_ms":  ts_now(),
        }


# ── HTTP Client wrapper ─────────────────────────────────────

class SimClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client: httpx.AsyncClient | None = None

    async def ensure_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def post(self, path: str, payload: dict) -> bool:
        """POST JSON to the API. Returns True on success, False on failure."""
        await self.ensure_client()
        try:
            resp = await self.client.post(path, json=payload)
            if resp.status_code >= 400:
                print(f"{C.RED}[{clock()}] [ERROR]    {path} returned {resp.status_code}: {resp.text[:120]}{C.RESET}")
                return False
            return True
        except httpx.ConnectError:
            print(f"{C.RED}[{clock()}] [ERROR]    Cannot connect to {self.base_url}{path} — is the API running?{C.RESET}")
            return False
        except Exception as e:
            print(f"{C.RED}[{clock()}] [ERROR]    {path}: {e}{C.RESET}")
            return False

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None


# ── Simulation Loops ─────────────────────────────────────────

async def ambient_loop(client: SimClient, ambient: AmbientGenerator):
    """POST /ingest/ambient for ZONE_A and ZONE_B every 3 seconds."""
    while True:
        for zone_id in ("ZONE_A", "ZONE_B"):
            payload = ambient.generate(zone_id)
            ok = await client.post("/ingest/ambient", payload)
            if ok:
                t   = payload["temperature_c"]
                co2 = payload["co2_ppm"]
                hum = payload["humidity_pct"]
                pm  = payload["pm25"]
                lpg = payload["lpg_ppm"]
                prs = payload["pressure_hpa"]
                print(
                    f"{C.GREEN}[{clock()}] [AMBIENT]  {zone_id}  "
                    f"temp={t}°C  hum={hum}%  co2={co2}ppm  pm25={pm}µg/m³  "
                    f"lpg={lpg}ppm  pres={prs}hPa{C.RESET}"
                )
        await asyncio.sleep(AMBIENT_INTERVAL)


async def machine_loop(client: SimClient, machine: MachineState):
    """POST /ingest/machine every 1 second."""
    while True:
        machine.update()
        payload = {
            "node":         "compressor",
            "state":        machine.state,
            "temp_c":       machine.temp_c,
            "rpm":          machine.rpm,
            "vibration_g":  machine.vibration_g,
            "power_w":      machine.power_w,
            "ts_ms":        int(time.time() * 1000),
            "pressure_bar": machine.pressure_bar,
            "oil_temp_c":   machine.oil_temp_c,
            "airflow_lpm":  machine.airflow_lpm,
        }
        ok = await client.post("/ingest/machine", payload)
        if ok:
            sc = color_for_state(machine.state)
            print(
                f"{sc}[{clock()}] [MACHINE]  {machine.state:<10}  "
                f"rpm={payload['rpm']}  vib={payload['vibration_g']}g  "
                f"temp={payload['temp_c']}°C  "
                f"pwr={payload['power_w']}W  "
                f"prs={payload['pressure_bar']}bar  "
                f"oil={payload['oil_temp_c']}°C{C.RESET}"
            )
        await asyncio.sleep(MACHINE_INTERVAL)


async def report_loop(client: SimClient, machine: MachineState):
    """POST /decision/report every 60 seconds, simulating MOD-04 LLM output."""
    # Wait a few seconds so there's data first
    await asyncio.sleep(5)
    while True:
        state = machine.state
        risk = RISK_MAP[state]
        hrs = FAILURE_HRS_MAP[state] + random.uniform(-0.5, 0.5)
        hrs = max(0, rnd(hrs, 1))
        anomalies = list(ANOMALY_MAP[state])  # copy
        confidence = rnd(random.uniform(0.65, 0.98), 2)

        payload = {
            "risk_level":            risk,
            "predicted_failure_hrs": hrs,
            "anomalies":             anomalies,
            "recommended_action":    ACTION_MAP[state],
            "confidence":            confidence,
            "timestamp_ms":          ts_now(),
        }

        ok = await client.post("/decision/report", payload)
        if ok:
            rc = risk_color(risk)
            icon = "🟢" if risk == "RISK_OK" else "🟡" if risk in ("RISK_WATCH", "RISK_WARN") else "🔴"
            print(
                f"{rc}[{clock()}] [REPORT]   {icon} {risk}  "
                f"failure_in={hrs}h  confidence={confidence}  "
                f"action={ACTION_MAP[state][:60]}{C.RESET}"
            )

        await asyncio.sleep(REPORT_INTERVAL)


async def actuator_loop(client: SimClient, machine: MachineState):
    """POST /decision/actuator when machine state is DEGRADING or worse.
    Simulates the Pi sending automated commands.
    """
    await asyncio.sleep(8)
    while True:
        state = machine.state
        if state in ("DEGRADING", "CRITICAL", "FAILURE"):
            # Fan speed proportional to severity
            fan_pct = {"DEGRADING": 60.0, "CRITICAL": 90.0, "FAILURE": 100.0}[state]

            payload = {
                "zone_id":      "ZONE_A",
                "device_type":  "DEV_FAN",
                "value_pct":    fan_pct,
                "relay_state":  True,
                "source":       "LLM",
                "timestamp_ms": ts_now(),
            }

            ok = await client.post("/decision/actuator", payload)
            if ok:
                sc = color_for_state(state)
                print(
                    f"{sc}[{clock()}] [ACTUATOR] ⚡ DEV_FAN → ZONE_A  "
                    f"value={fan_pct}%  relay=ON  source=LLM  "
                    f"(state={state}){C.RESET}"
                )

            # Also activate cooler when CRITICAL or FAILURE
            if state in ("CRITICAL", "FAILURE"):
                cooler_payload = {
                    "zone_id":      "ZONE_A",
                    "device_type":  "DEV_COOLER",
                    "value_pct":    100.0,
                    "relay_state":  True,
                    "source":       "LLM",
                    "timestamp_ms": ts_now(),
                }
                ok2 = await client.post("/decision/actuator", cooler_payload)
                if ok2:
                    print(
                        f"{sc}[{clock()}] [ACTUATOR] ⚡ DEV_COOLER → ZONE_A  "
                        f"value=100%  relay=ON  source=LLM{C.RESET}"
                    )

        await asyncio.sleep(10)


async def alarm_loop(client: SimClient, machine: MachineState):
    """Inject random alarm events every 30-40 seconds."""
    await asyncio.sleep(random.uniform(15, 25))
    while True:
        # Pick a random alarm scenario
        alarm_type = random.choice(["co2", "temp", "pm25", "machine_vib"])

        if alarm_type == "co2":
            zone = random.choice(["ZONE_A", "ZONE_B"])
            value = rnd(random.uniform(1000, 1500), 1)
            payload = {
                "source_module": "MOD-01",
                "sensor_field":  "co2_ppm",
                "value":         value,
                "threshold":     1000.0,
                "zone_id":       zone,
                "timestamp_ms":  ts_now(),
            }
        elif alarm_type == "temp":
            zone = random.choice(["ZONE_A", "ZONE_B"])
            value = rnd(random.uniform(40, 55), 1)
            payload = {
                "source_module": "MOD-01",
                "sensor_field":  "temperature_c",
                "value":         value,
                "threshold":     40.0,
                "zone_id":       zone,
                "timestamp_ms":  ts_now(),
            }
        elif alarm_type == "pm25":
            zone = random.choice(["ZONE_A", "ZONE_B"])
            value = rnd(random.uniform(35, 60), 1)
            payload = {
                "source_module": "MOD-01",
                "sensor_field":  "pm25",
                "value":         value,
                "threshold":     35.0,
                "zone_id":       zone,
                "timestamp_ms":  ts_now(),
            }
        else:  # machine_vib
            value = rnd(random.uniform(2.0, 5.0), 2)
            payload = {
                "source_module": "MOD-02",
                "sensor_field":  "vibration_g",
                "value":         value,
                "threshold":     2.0,
                "zone_id":       "MACHINE",
                "timestamp_ms":  ts_now(),
            }

        ok = await client.post("/ingest/alarm", payload)
        if ok:
            print(
                f"{C.RED}{C.BOLD}[{clock()}] [ALARM]    ⚠ {payload['zone_id']}  "
                f"{payload['sensor_field']}={payload['value']} > {payload['threshold']}{C.RESET}"
            )

        interval = random.uniform(ALARM_INTERVAL_MIN, ALARM_INTERVAL_MAX)
        await asyncio.sleep(interval)


async def cleanup_loop(client: SimClient):
    """Periodically prune old sensor readings to prevent unbounded DB growth."""
    await asyncio.sleep(600)  # wait 10 min before first cleanup
    while True:
        ok = await client.post("/admin/cleanup", {})
        if ok:
            print(f"{C.DIM}[{clock()}] [CLEANUP]  Old sensor readings pruned{C.RESET}")
        await asyncio.sleep(600)


# ── Startup & Health Check ───────────────────────────────────

async def wait_for_api(client: SimClient):
    """Wait until the API is reachable before starting simulation."""
    print(f"{C.CYAN}[{clock()}] Connecting to API at {client.base_url} ...{C.RESET}")
    while True:
        await client.ensure_client()
        try:
            resp = await client.client.get("/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"{C.GREEN}{C.BOLD}[{clock()}] ✓ API is online!{C.RESET}")
                print(f"{C.DIM}         status={data.get('status')}  "
                      f"pi_reachable={data.get('pi_reachable')}  "
                      f"ws_clients={data.get('websocket_clients')}{C.RESET}")
                return
        except Exception:
            pass
        print(f"{C.YELLOW}[{clock()}] API not reachable. Retrying in 5 seconds...{C.RESET}")
        await asyncio.sleep(5)


def print_banner():
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════╗
║         🏭  Dark Factory — Hardware Simulator  🏭            ║
║         Fake ESP32 + Fake Pi  →  MOD-05 API                  ║
╚══════════════════════════════════════════════════════════════╝{C.RESET}

{C.DIM}  Loops:
    • Ambient sensors   → POST /ingest/ambient   (every {AMBIENT_INTERVAL}s, ZONE_A + ZONE_B)
    • Machine telemetry → POST /ingest/machine   (every {MACHINE_INTERVAL}s)
    • LLM reports       → POST /decision/report  (every {REPORT_INTERVAL}s)
    • Actuator cmds     → POST /decision/actuator (on DEGRADING+)
    • Alarm injection   → POST /ingest/alarm     (every ~{ALARM_INTERVAL_MIN}-{ALARM_INTERVAL_MAX}s)

  State machine:  NORMAL → HEATING → DEGRADING → CRITICAL → FAILURE
                  ({STATE_TICKS} ticks per state, lerp α={LERP_ALPHA})
{C.RESET}
{C.BOLD}  Press Ctrl+C to stop.{C.RESET}
""")


# ── Main ─────────────────────────────────────────────────────

async def main(base_url: str):
    print_banner()

    client  = SimClient(base_url)
    machine = MachineState()
    ambient = AmbientGenerator()

    await wait_for_api(client)

    # Clean the database for a fresh start
    ok = await client.post("/admin/reset-db", {})
    if ok:
        print(f"{C.CYAN}{C.BOLD}[{clock()}] 🗑  Database cleared — fresh start{C.RESET}")
    else:
        print(f"{C.YELLOW}[{clock()}] ⚠ Could not clear database — continuing with existing data{C.RESET}")

    print(f"\n{C.GREEN}{C.BOLD}[{clock()}] ▶ Simulation started!{C.RESET}\n")

    try:
        await asyncio.gather(
            ambient_loop(client, ambient),
            machine_loop(client, machine),
            report_loop(client, machine),
            actuator_loop(client, machine),
            alarm_loop(client, machine),
            cleanup_loop(client),
        )
    except asyncio.CancelledError:
        pass
    finally:
        await client.close()
        print(f"\n{C.CYAN}[{clock()}] Simulation stopped.{C.RESET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dark Factory Hardware Simulator")
    parser.add_argument(
        "--url",
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.url))
    except KeyboardInterrupt:
        print(f"\n{C.CYAN}Bye! 👋{C.RESET}")
        sys.exit(0)
