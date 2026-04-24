# SENEC Home Assistant Integration (Local API)

Read energy data from a **SENEC** home battery/inverter system via its local HTTP API and expose it as sensors in **Home Assistant**.

## How It Works

```
┌──────────┐   curl POST    ┌──────────────┐   decode    ┌──────────────────┐
│  SENEC   │ ─────────────► │ senec_read.sh │ ─────────► │ pv_values.json   │
│ Inverter │   /lala.cgi    │ + decode.py   │            │ (human-readable) │
└──────────┘                └──────────────┘            └────────┬─────────┘
                                                                 │
                                                          cat + jq / HA
                                                                 │
                                                        ┌────────▼─────────┐
                                                        │  Home Assistant  │
                                                        │  Sensors         │
                                                        └──────────────────┘
```

1. **`senec_read.sh`** — POSTs a JSON request to the SENEC device's local API (`/lala.cgi`), pipes the hex-encoded response through `senec_decode.py`, and writes the decoded result to `pv_values.json`.
2. **`senec_decode.py`** — Decodes SENEC's proprietary hex-prefixed values (IEEE 754 floats, signed/unsigned ints) into plain numbers and adds computed summary fields.
3. **Helper scripts** (`battery_level.sh`, `grid.sh`, etc.) — Tiny `jq` one-liners that extract individual values from the JSON. Useful for testing but not required by the HA integration.
4. **Home Assistant `command_line` sensors** — Read the JSON file every 30 seconds and expose all values as HA entities with proper `device_class`, `unit_of_measurement`, and `state_class` for the Energy Dashboard.

## Sensors Provided

| Sensor | Unit | Description |
|--------|------|-------------|
| `sensor.senec_solar_power` | W | Total PV inverter output |
| `sensor.senec_house_power` | W | Current house consumption |
| `sensor.senec_grid_power` | W | Grid exchange (negative = export) |
| `sensor.senec_grid_export` | W | Grid feed-in (≥ 0) |
| `sensor.senec_grid_import` | W | Grid draw (≥ 0) |
| `sensor.senec_battery_power` | W | Battery power (positive = charging) |
| `sensor.senec_battery_charging` | W | Charging power (≥ 0) |
| `sensor.senec_battery_discharging` | W | Discharging power (≥ 0) |
| `sensor.senec_battery_level` | % | Battery state of charge |
| `sensor.senec_battery_dc_current` | A | Battery DC current |
| `sensor.senec_mpp2_power` | W | PV string 2 power |
| `sensor.senec_mpp3_power` | W | PV string 3 power |
| `sensor.senec_self_consumption` | % | Self-consumption ratio |
| `sensor.senec_system_state` | — | Numeric system state code |
| `sensor.senec_system_state_text` | — | Human-readable system state |

## Installation

### 1. Copy scripts to Home Assistant

Copy the scripts into your HA config directory:

```bash
mkdir -p /config/pv
cp senec_read.sh senec_decode.py /config/pv/
cp battery_level.sh battery_power.sh grid.sh house_power.sh \
   mpp2.sh mpp3.sh power_generation.sh /config/pv/
chmod +x /config/pv/*.sh
```

### 2. Adjust the SENEC IP address

Edit `/config/pv/senec_read.sh` and change the IP to match your SENEC device:

```bash
# In senec_read.sh, change this line:
curl -s -k -X POST "https://192.168.178.27/lala.cgi" \
```

### 3. Verify the scripts work

From the HA terminal (or SSH add-on):

```bash
cd /config/pv
bash senec_read.sh /config/pv/pv_values.json
cat /config/pv/pv_values.json
```

You should see decoded JSON with a `summary` section containing power values.

### 4. Add the Home Assistant configuration

Merge the contents of [`homeassistant/configuration.yaml`](homeassistant/configuration.yaml) into your existing HA `configuration.yaml`. The file contains:

- A `shell_command` to trigger data fetching
- `command_line` sensors that read the JSON
- `template` sensors for derived values (grid import/export split, charge/discharge split, self-consumption)
- An `automation` that refreshes data every 30 seconds

Optionally, merge [`homeassistant/customize.yaml`](homeassistant/customize.yaml) for icons and friendly names:

```yaml
# In configuration.yaml
homeassistant:
  customize: !include customize.yaml
```

### 5. Restart Home Assistant

Go to **Settings → System → Restart** or run:

```bash
ha core restart
```

### 6. (Optional) Energy Dashboard

The sensors use proper `device_class` and `state_class` attributes, so they can be used with the HA Energy Dashboard. However, the Energy Dashboard requires **energy sensors** (kWh), not power sensors (W). You can create [Riemann sum integral](https://www.home-assistant.io/integrations/integration/) helpers to convert:

```yaml
# Add to configuration.yaml
sensor:
  - platform: integration
    source: sensor.senec_solar_power
    name: "SENEC Solar Energy"
    unit_prefix: k
    round: 2

  - platform: integration
    source: sensor.senec_grid_import
    name: "SENEC Grid Energy Import"
    unit_prefix: k
    round: 2

  - platform: integration
    source: sensor.senec_grid_export
    name: "SENEC Grid Energy Export"
    unit_prefix: k
    round: 2

  - platform: integration
    source: sensor.senec_battery_charging
    name: "SENEC Battery Energy In"
    unit_prefix: k
    round: 2

  - platform: integration
    source: sensor.senec_battery_discharging
    name: "SENEC Battery Energy Out"
    unit_prefix: k
    round: 2

  - platform: integration
    source: sensor.senec_house_power
    name: "SENEC House Energy"
    unit_prefix: k
    round: 2
```

Then configure the Energy Dashboard under **Settings → Dashboards → Energy**.

## Dependencies

These must be available inside the Home Assistant container:

- **`curl`** — HTTP requests to the SENEC device
- **`python3`** — Runs the decoder script
- **`jq`** — JSON parsing in helper scripts (optional if only using HA sensors)

Most HA OS / container installations include `curl` and `python3`. If `jq` is missing, install it via the SSH add-on:

```bash
apk add jq
```

## File Structure

```
.
├── senec_read.sh          # Main data fetcher (curl + decode)
├── senec_decode.py        # Hex-to-human decoder
├── battery_level.sh       # Helper: battery SOC
├── battery_power.sh       # Helper: battery power
├── grid.sh                # Helper: grid power
├── house_power.sh         # Helper: house consumption
├── mpp2.sh                # Helper: string 2 power
├── mpp3.sh                # Helper: string 3 power
├── power_generation.sh    # Helper: total generation
├── ex.json                # Example decoded output
├── homeassistant/
│   ├── configuration.yaml # HA sensor & automation config
│   └── customize.yaml     # Icons and friendly names
└── README.md
```

## Troubleshooting

- **Sensors show `unknown`**: Check that `/config/pv/pv_values.json` exists and contains valid JSON. Run `senec_read.sh` manually to verify.
- **`curl` SSL errors**: The `-k` flag in `senec_read.sh` disables certificate verification (SENEC uses self-signed certs). This is expected.
- **Stale data**: The automation runs every 30 seconds. Check **Settings → Automations** to verify `senec_periodic_update` is enabled.
- **Permission denied**: Ensure scripts are executable: `chmod +x /config/pv/*.sh`
