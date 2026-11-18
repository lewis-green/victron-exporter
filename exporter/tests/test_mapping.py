import pytest

from victron_exporter.mapping import FIXED, HELP, Sample, lookup, parse_value, subscriptions


def test_lookup_fixed_topic_ignores_instance():
    assert lookup("battery/512/Soc") == Sample("victron_battery_soc_percent", ())
    assert lookup("battery/7/Soc") == Sample("victron_battery_soc_percent", ())
    assert lookup("system/0/Control/EffectiveChargeVoltage") == Sample(
        "victron_battery_charge_voltage_limit_volts", ())


def test_lookup_alarm_carries_source_and_name():
    assert lookup("vebus/288/Alarms/Overload") == Sample(
        "victron_alarm", (("source", "vebus"), ("alarm", "Overload")))
    assert lookup("battery/512/Alarms/HighTemperature") == Sample(
        "victron_alarm", (("source", "battery"), ("alarm", "HighTemperature")))


def test_lookup_skips_per_phase_alarms_and_unknown_topics():
    assert lookup("vebus/288/Alarms/L1/Overload") is None
    assert lookup("battery/512/History/ChargedEnergy") is None
    assert lookup("system/0/Alarms/Foo") is None
    assert lookup("heartbeat") is None


def test_every_metric_has_help_text():
    for metric in set(FIXED.values()) | {"victron_alarm"}:
        assert metric in HELP


@pytest.mark.parametrize("payload,expected", [
    (b'{"value": 98.0}', 98.0),
    (b'{"value": 3}', 3.0),
    (b'{"value": true}', 1.0),
    (b'{"value": null}', None),
    (b"", None),
])
def test_parse_value(payload, expected):
    assert parse_value(payload) == expected


@pytest.mark.parametrize("payload", [b"not json", b'{"value": "abc"}', b'{"other": 1}', b"[1]"])
def test_parse_value_rejects_malformed(payload):
    with pytest.raises(ValueError):
        parse_value(payload)


def test_subscriptions_cover_fixed_topics_alarms_and_heartbeat():
    subs = subscriptions("abc")
    assert "N/abc/battery/+/Soc" in subs
    assert "N/abc/system/+/Control/EffectiveChargeVoltage" in subs
    assert "N/abc/battery/+/Alarms/#" in subs
    assert "N/abc/vebus/+/Alarms/#" in subs
    assert "N/abc/heartbeat" in subs
    assert len(subs) == len(set(subs))
