"""Map Venus OS MQTT topics to Prometheus metrics."""
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    metric: str
    labels: tuple  # extra labels as ((name, value), ...), excluding "feed"


# (service, path below the device instance) -> metric name
FIXED = {
    ("vebus", "Ac/ActiveIn/Connected"): "victron_grid_connected",
    ("vebus", "State"): "victron_vebus_state",
    ("vebus", "Ac/ActiveIn/L1/V"): "victron_ac_input_voltage_volts",
    ("vebus", "Ac/ActiveIn/L1/P"): "victron_ac_input_power_watts",
    ("vebus", "Ac/Out/L1/P"): "victron_ac_output_power_watts",
    ("vebus", "Ac/Out/L1/V"): "victron_ac_output_voltage_volts",
    ("vebus", "Dc/0/Power"): "victron_vebus_dc_power_watts",
    ("battery", "Soc"): "victron_battery_soc_percent",
    ("battery", "Dc/0/Voltage"): "victron_battery_voltage_volts",
    ("battery", "Dc/0/Current"): "victron_battery_current_amperes",
    ("battery", "Dc/0/Power"): "victron_battery_power_watts",
    ("battery", "Dc/0/Temperature"): "victron_battery_temperature_celsius",
    ("battery", "System/MinCellVoltage"): "victron_battery_cell_voltage_min_volts",
    ("battery", "System/MaxCellVoltage"): "victron_battery_cell_voltage_max_volts",
    ("system", "Control/EffectiveChargeVoltage"): "victron_battery_charge_voltage_limit_volts",
    ("battery", "Info/MaxChargeVoltage"): "victron_battery_bms_charge_voltage_volts",
    ("battery", "Info/MaxChargeCurrent"): "victron_battery_bms_charge_current_limit_amperes",
}

ALARM_SERVICES = ("battery", "vebus")

HELP = {
    "victron_grid_connected": "1 if the inverter's AC input is connected, 0 if running on battery.",
    "victron_vebus_state": "VE.Bus state code (3 bulk, 4 absorption, 5 float, 8 passthru, 9 inverting).",
    "victron_ac_input_voltage_volts": "AC input voltage, L1.",
    "victron_ac_input_power_watts": "AC input power, L1.",
    "victron_ac_output_power_watts": "AC output (load) power, L1.",
    "victron_ac_output_voltage_volts": "AC output voltage, L1.",
    "victron_vebus_dc_power_watts": "Inverter/charger DC power; positive is into the DC side.",
    "victron_battery_soc_percent": "Battery state of charge reported by the BMS.",
    "victron_battery_voltage_volts": "Battery voltage reported by the BMS.",
    "victron_battery_current_amperes": "Battery current; positive is charging.",
    "victron_battery_power_watts": "Battery power; positive is charging.",
    "victron_battery_temperature_celsius": "Battery temperature.",
    "victron_battery_cell_voltage_min_volts": "Lowest cell voltage.",
    "victron_battery_cell_voltage_max_volts": "Highest cell voltage.",
    "victron_battery_charge_voltage_limit_volts": "Charge voltage limit in effect on the GX (DVCC).",
    "victron_battery_bms_charge_voltage_volts": "Charge voltage requested by the BMS.",
    "victron_battery_bms_charge_current_limit_amperes": "Charge current limit requested by the BMS.",
    "victron_alarm": "Alarm state: 0 ok, 1 warning, 2 alarm.",
}


def lookup(suffix):
    """Return the Sample for a topic suffix '<service>/<instance>/<path>', or None."""
    parts = suffix.split("/", 2)
    if len(parts) < 3:
        return None
    service, _instance, path = parts
    metric = FIXED.get((service, path))
    if metric is not None:
        return Sample(metric, ())
    if service in ALARM_SERVICES and path.startswith("Alarms/"):
        name = path[len("Alarms/"):]
        if name and "/" not in name:
            return Sample("victron_alarm", (("source", service), ("alarm", name)))
    return None


def parse_value(payload):
    """Return the numeric value of a Venus payload, None if cleared; ValueError if malformed."""
    if not payload:
        return None
    doc = json.loads(payload)
    if not isinstance(doc, dict) or "value" not in doc:
        raise ValueError("payload has no 'value'")
    value = doc["value"]
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return float(value)
    raise ValueError("value is not numeric")


def subscriptions(portal):
    """Topic filters to subscribe to for one GX."""
    subs = [f"N/{portal}/{service}/+/{path}" for service, path in FIXED]
    subs += [f"N/{portal}/{service}/+/Alarms/#" for service in ALARM_SERVICES]
    subs.append(f"N/{portal}/heartbeat")
    return subs
