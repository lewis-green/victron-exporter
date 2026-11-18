#!/usr/bin/env python3
"""Generate grafana/victron-ups-feeds.json. Run: python grafana/build_dashboard.py"""
import json
import pathlib

DS = {"type": "prometheus", "uid": "${datasource}"}
F = '{feed=~"$feed"}'
panels = []


def add(panel_type, title, exprs, x, y, w, h, unit=None, **extra):
    targets = []
    for i, item in enumerate(exprs):
        expr, legend = item if isinstance(item, tuple) else (item, "{{feed}}")
        targets.append({"datasource": DS, "expr": expr, "legendFormat": legend, "refId": chr(65 + i)})
    defaults = {"unit": unit} if unit else {}
    defaults.update(extra.pop("defaults", {}))
    panel = {"id": len(panels) + 1, "type": panel_type, "title": title, "datasource": DS,
             "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": targets,
             "fieldConfig": {"defaults": defaults, "overrides": []}}
    panel.update(extra)
    panels.append(panel)


def row(title, y):
    panels.append({"id": len(panels) + 1, "type": "row", "title": title, "collapsed": False,
                   "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []})


def value_map(options):
    return [{"type": "value", "options": {str(k): {"text": text, "color": color, "index": i}
                                          for i, (k, text, color) in enumerate(options)}}]


STAT = {"options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "background",
                    "graphMode": "none", "textMode": "value_and_name"}}
GRID = value_map([(0, "On battery", "red"), (1, "Grid", "green")])
STATE = value_map([(0, "Off", "red"), (1, "Low power", "blue"), (2, "Fault", "red"), (3, "Bulk", "blue"),
                   (4, "Absorption", "green"), (5, "Float", "green"), (6, "Storage", "green"),
                   (7, "Equalize", "blue"), (8, "Passthru", "green"), (9, "Inverting", "orange"),
                   (10, "Power assist", "orange"), (11, "Power supply", "blue"),
                   (252, "External control", "green")])
SOC_STEPS = {"mode": "absolute", "steps": [{"color": "red", "value": None},
                                           {"color": "orange", "value": 25}, {"color": "green", "value": 50}]}
ALARM_STEPS = {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]}

row("Status", 0)
add("stat", "Grid", [f"victron_grid_connected{F}"], 0, 1, 5, 4, defaults={"mappings": GRID}, **STAT)
add("stat", "Inverter state", [f"victron_vebus_state{F}"], 5, 1, 5, 4, defaults={"mappings": STATE}, **STAT)
add("stat", "State of charge", [f"victron_battery_soc_percent{F}"], 10, 1, 5, 4, "percent",
    defaults={"thresholds": SOC_STEPS, "min": 0, "max": 100}, **STAT)
add("stat", "Load", [f"victron_ac_output_power_watts{F}"], 15, 1, 5, 4, "watt",
    options={"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "none", "graphMode": "area",
             "textMode": "value_and_name"})
add("stat", "Active alarms", [f"count by (feed) (victron_alarm{F} > 0) or victron_up{F} * 0"], 20, 1, 4, 4,
    defaults={"thresholds": ALARM_STEPS}, **STAT)

row("Battery", 5)
add("timeseries", "State of charge", [f"victron_battery_soc_percent{F}"], 0, 6, 8, 8, "percent",
    defaults={"min": 0, "max": 100})
add("timeseries", "Battery voltage and charge limit",
    [f"victron_battery_voltage_volts{F}", (f"victron_battery_charge_voltage_limit_volts{F}", "{{feed}} limit")],
    8, 6, 8, 8, "volt")
add("timeseries", "Battery current (positive is charging)", [f"victron_battery_current_amperes{F}"],
    16, 6, 8, 8, "amp")

row("Cells", 14)
add("timeseries", "Cell voltage, min and max",
    [(f"victron_battery_cell_voltage_max_volts{F}", "{{feed}} max"),
     (f"victron_battery_cell_voltage_min_volts{F}", "{{feed}} min")], 0, 15, 12, 8, "volt")
add("timeseries", "Cell spread",
    [f"(victron_battery_cell_voltage_max_volts{F} - victron_battery_cell_voltage_min_volts{F}) * 1000"],
    12, 15, 6, 8, "mvolt")
add("timeseries", "Battery temperature", [f"victron_battery_temperature_celsius{F}"], 18, 15, 6, 8, "celsius")

row("Power", 23)
add("timeseries", "AC power",
    [(f"victron_ac_input_power_watts{F}", "{{feed}} input"),
     (f"victron_ac_output_power_watts{F}", "{{feed}} output")], 0, 24, 12, 8, "watt")
add("timeseries", "Inverter DC power", [f"victron_vebus_dc_power_watts{F}"], 12, 24, 6, 8, "watt")
add("timeseries", "AC input voltage", [f"victron_ac_input_voltage_volts{F}"], 18, 24, 6, 8, "volt")

row("Alarms and collection health", 32)
add("state-timeline", "Active alarms (1 warning, 2 alarm)",
    [(f"victron_alarm{F} > 0", "{{feed}} {{source}} {{alarm}}")], 0, 33, 12, 7,
    defaults={"thresholds": {"mode": "absolute", "steps": [{"color": "orange", "value": None},
                                                           {"color": "red", "value": 2}]}})
add("timeseries", "Exporter connected to GX", [f"victron_up{F}"], 12, 33, 6, 7, defaults={"min": 0, "max": 1})
add("timeseries", "Age of last update", [f"time() - victron_last_update_timestamp_seconds{F}"], 18, 33, 6, 7, "s")

dashboard = {
    "uid": "victron-ups-feeds", "title": "Victron UPS feeds", "tags": ["victron", "ups"],
    "schemaVersion": 39, "version": 1, "editable": True, "refresh": "30s",
    "time": {"from": "now-24h", "to": "now"}, "timezone": "browser",
    "templating": {"list": [
        {"name": "datasource", "label": "Data source", "type": "datasource", "query": "prometheus",
         "current": {}, "hide": 0},
        {"name": "feed", "label": "Feed", "type": "query", "datasource": DS,
         "query": {"query": "label_values(victron_up, feed)", "refId": "feed"},
         "definition": "label_values(victron_up, feed)", "refresh": 2, "multi": True, "includeAll": True,
         "current": {"text": "All", "value": "$__all"}, "sort": 1},
    ]},
    "panels": panels,
}

out = pathlib.Path(__file__).with_name("victron-ups-feeds.json")
out.write_text(json.dumps(dashboard, indent=2) + "\n")
print(f"wrote {out} with {len(panels)} panels")
