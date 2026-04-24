#!/usr/bin/env bash
# senec_read.sh - Read SENEC energy data and decode to human-readable JSON
#
# Usage: ./senec_read.sh

SENEC_IP="192.168.0.2" # enter the IP of your SENEC battery here

DEST=${1:-/config/pv/pv_values.json}

curl -s -k -X POST "${SENEC_IP}/lala.cgi" \
  -H "Content-Type: application/json" \
  -d '{
    "ENERGY": {
      "GUI_INVERTER_POWER": "",
      "GUI_HOUSE_POW": "",
      "GUI_GRID_POW": "",
      "GUI_BAT_DATA_POWER": "",
      "GUI_BAT_DATA_FUEL_CHARGE": "",
      "STAT_STATE": ""
    },
    "PV1": {
      "MPP_POWER": "",
      "MPP_VOL": "",
      "MPP_CUR": "",
      "POWER_RATIO": ""
    },
    "BAT1OBJ1": {
      "I_DC": ""
    },
    "BMS": {
      "NR_INSTALLED": ""
    }
  }' | python3 senec_decode.py > "${DEST}"
