from esphome import core
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.core import CORE, ID
from esphome.cpp_generator import MockObj, MockObjClass
from esphome.components import (
    climate,
    switch,
    sensor,
    text_sensor,
    binary_sensor,
    number,
    select,
)
from esphome.const import (
    CONF_ENTITY_CATEGORY,
    CONF_ICON,
    CONF_ID,
    CONF_INVERTED,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VERSION,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_DURATION,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_NONE,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_MINUTE,
    UNIT_SECOND,
)
from .. import vport  # pylint: disable=relative-beyond-top-level


CODEOWNERS = ["@dentra"]
# ESP_PLATFORMS = [PLATFORM_ESP32]
# DEPENDENCIES = ["ble_client"]
AUTO_LOAD = [
    "etl",
    "tion-api",
    "sensor",
    "switch",
    "text_sensor",
    "binary_sensor",
    "number",
    "select",
    "climate",
]

ICON_AIR_FILTER = "mdi:air-filter"

CONF_TION_API_BASE_ID = "tion_api_base_id"
CONF_TION_API_ID = "tion_api_id"
CONF_STATE_TIMEOUT = "state_timeout"

CONF_BUZZER = "buzzer"
CONF_OUTDOOR_TEMPERATURE = "outdoor_temperature"
CONF_FILTER_TIME_LEFT = "filter_time_left"
CONF_BOOST_TIME = "boost_time"
CONF_BOOST_TIME_LEFT = "boost_time_left"
CONF_PRESETS = "presets"
CONF_PRESET_MODE = "mode"
CONF_PRESET_FAN_SPEED = "fan_speed"
CONF_PRESET_TARGET_TEMPERATURE = "target_temperature"

UNIT_DAYS = "d"

tion_ns = cg.esphome_ns.namespace("tion")
TionBoostTimeNumber = tion_ns.class_("TionBoostTimeNumber", number.Number)
TionSwitch = tion_ns.class_("TionSwitch", switch.Switch)
TionVPortApi = tion_ns.class_("TionVPortApi")

PRESET_MODES = {
    "off": climate.ClimateMode.CLIMATE_MODE_OFF,
    "heat": climate.ClimateMode.CLIMATE_MODE_HEAT,
    "fan_only": climate.ClimateMode.CLIMATE_MODE_FAN_ONLY,
}

PRESET_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_PRESET_MODE): cv.one_of(*PRESET_MODES, lower=True),
        cv.Optional(CONF_PRESET_FAN_SPEED): cv.int_range(min=1, max=6),
        cv.Optional(CONF_PRESET_TARGET_TEMPERATURE): cv.int_range(min=1, max=25),
    }
)

PRESETS_SCHEMA = cv.Schema(
    {
        cv.Optional("home"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("away"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("boost"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("comfort"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("eco"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("sleep"): cv.Any(PRESET_SCHEMA, None),
        cv.Optional("activity"): cv.Any(PRESET_SCHEMA, None),
    }
)


def tion_schema(tion_class: MockObjClass, tion_api_class: MockObjClass):
    """Declare base tion schema"""
    return (
        climate.CLIMATE_SCHEMA.extend(
            {
                cv.GenerateID(): cv.declare_id(tion_class),
                cv.GenerateID(CONF_TION_API_BASE_ID): cv.declare_id(tion_api_class),
                cv.GenerateID(CONF_TION_API_ID): cv.declare_id(TionVPortApi),
                cv.Optional(CONF_ICON, default=ICON_AIR_FILTER): cv.icon,
                cv.Optional(CONF_BUZZER): switch.SWITCH_SCHEMA.extend(
                    {
                        cv.GenerateID(): cv.declare_id(TionSwitch),
                        cv.Optional(CONF_ICON, default="mdi:volume-high"): cv.icon,
                        cv.Optional(
                            CONF_ENTITY_CATEGORY, default=ENTITY_CATEGORY_CONFIG
                        ): cv.entity_category,
                        cv.Optional(CONF_INVERTED): cv.invalid(
                            "Inverted mode is not supported"
                        ),
                    }
                ),
                cv.Optional(CONF_OUTDOOR_TEMPERATURE): sensor.sensor_schema(
                    unit_of_measurement=UNIT_CELSIUS,
                    accuracy_decimals=0,
                    device_class=DEVICE_CLASS_TEMPERATURE,
                    state_class=STATE_CLASS_MEASUREMENT,
                    entity_category=ENTITY_CATEGORY_NONE,
                ),
                cv.Optional(CONF_VERSION): text_sensor.TEXT_SENSOR_SCHEMA.extend(
                    {
                        cv.GenerateID(): cv.declare_id(text_sensor.TextSensor),
                        cv.Optional(CONF_ICON, default="mdi:git"): cv.icon,
                        cv.Optional(
                            CONF_ENTITY_CATEGORY, default=ENTITY_CATEGORY_DIAGNOSTIC
                        ): cv.entity_category,
                    }
                ),
                cv.Optional(CONF_FILTER_TIME_LEFT): sensor.sensor_schema(
                    unit_of_measurement=UNIT_DAYS,
                    accuracy_decimals=0,
                    icon=ICON_AIR_FILTER,
                    device_class=DEVICE_CLASS_DURATION,
                    state_class=STATE_CLASS_MEASUREMENT,
                    entity_category=ENTITY_CATEGORY_NONE,
                ),
                cv.Optional(CONF_BOOST_TIME): number.NUMBER_SCHEMA.extend(
                    {
                        cv.GenerateID(): cv.declare_id(TionBoostTimeNumber),
                        cv.Optional(CONF_ICON, default="mdi:clock-fast"): cv.icon,
                        cv.Optional(
                            CONF_UNIT_OF_MEASUREMENT, default=UNIT_MINUTE
                        ): cv.string_strict,
                        cv.Optional(
                            CONF_ENTITY_CATEGORY, default=ENTITY_CATEGORY_CONFIG
                        ): cv.entity_category,
                    }
                ),
                cv.Optional(CONF_BOOST_TIME_LEFT): sensor.sensor_schema(
                    unit_of_measurement=UNIT_SECOND,
                    accuracy_decimals=1,
                    icon="mdi:clock-end",
                    device_class=DEVICE_CLASS_DURATION,
                    state_class=STATE_CLASS_MEASUREMENT,
                    entity_category=ENTITY_CATEGORY_NONE,
                ),
                cv.Optional(CONF_PRESETS): PRESETS_SCHEMA,
            }
        )
        .extend(vport.VPORT_CLIENT_SCHEMA)
        .extend(cv.polling_component_schema("60s"))
    )


def tion_vport_ble_schema(vport_class: MockObjClass, io_class: MockObjClass):
    return vport.vport_ble_schema(vport_class, io_class, "60s").extend(
        {
            cv.Optional(
                CONF_STATE_TIMEOUT, default="15s"
            ): cv.positive_time_period_milliseconds,
        }
    )


async def setup_binary_sensor(config, key, setter):
    """Setup binary sensor"""
    if key not in config:
        return None
    conf = config[key]
    sens = cg.new_Pvariable(conf[CONF_ID])
    await binary_sensor.register_binary_sensor(sens, conf)
    cg.add(setter(sens))
    return sens


async def setup_switch(config, key, setter, parent):
    """Setup switch"""
    if key not in config:
        return None
    conf = config[key]
    swch = cg.new_Pvariable(conf[CONF_ID], parent)
    await switch.register_switch(swch, conf)
    cg.add(setter(swch))
    return swch


async def setup_sensor(config, key, setter):
    """Setup sensor"""
    if key not in config:
        return None
    sens = await sensor.new_sensor(config[key])
    cg.add(setter(sens))
    return sens


async def setup_text_sensor(config, key, setter):
    """Setup text sensor"""
    if key not in config:
        return None
    conf = config[key]
    sens = cg.new_Pvariable(conf[CONF_ID])
    await text_sensor.register_text_sensor(sens, conf)
    cg.add(setter(sens))
    return sens


async def setup_number(
    config: dict, key: str, setter, min_value: int, max_value: int, step: int
):
    """Setup number"""
    if key not in config:
        return None
    numb = await number.new_number(
        config[CONF_BOOST_TIME], min_value=min_value, max_value=max_value, step=step
    )
    cg.add(setter(numb))
    return numb


async def setup_select(config, key, setter, parent, options):
    """Setup select"""
    if key not in config:
        return None
    conf = config[key]
    slct = cg.new_Pvariable(conf[CONF_ID], parent)
    await select.register_select(slct, conf, options=options)
    cg.add(setter(slct))
    return slct


async def setup_presets(config, key, setter) -> bool:
    """Setup presets"""
    if key not in config:
        return None
    conf = config[key]
    has_presets = False
    for _, (preset, options) in enumerate(conf.items()):
        preset = climate.CLIMATE_PRESETS[preset.upper()]
        options = options or {}
        mode = (
            PRESET_MODES[options[CONF_PRESET_MODE]]
            if CONF_PRESET_MODE in options
            else climate.ClimateMode.CLIMATE_MODE_AUTO
        )
        fan_speed = options.get(CONF_PRESET_FAN_SPEED, 0)
        target_temperature = options.get(CONF_PRESET_TARGET_TEMPERATURE, 0)
        cg.add(setter(preset, mode, fan_speed, target_temperature))
        if not has_presets:
            has_presets = True
            cg.add_build_flag("-DTION_ENABLE_PRESETS")
    return has_presets


async def setup_tion_core(config):
    """Setup core component properties"""

    prt = await vport.vport_get_var(config)
    api = cg.new_Pvariable(
        config[CONF_TION_API_ID],
        cg.TemplateArguments(
            # cg.MockObj(prt_io_id.type, "::").frame_spec_type,
            vport.vport_find(config).type.class_("frame_spec_type"),
            config[CONF_TION_API_BASE_ID].type,
        ),
        prt,
    )
    var = cg.new_Pvariable(config[CONF_ID], api)
    await cg.register_component(var, config)
    await climate.register_climate(var, config)

    # FIXME check and replace/remove
    cg.add(prt.set_api(api))
    cg.add(prt.set_state_type(api.get_state_type()))
    cg.add(var.set_vport_type(prt.get_vport_type()))

    await setup_switch(config, CONF_BUZZER, var.set_buzzer, var)
    await setup_sensor(config, CONF_OUTDOOR_TEMPERATURE, var.set_outdoor_temperature)
    await setup_sensor(config, CONF_FILTER_TIME_LEFT, var.set_filter_time_left)
    await setup_text_sensor(config, CONF_VERSION, var.set_version)
    has_presets = await setup_presets(config, CONF_PRESETS, var.update_preset)
    if has_presets and "boost" in config[CONF_PRESETS]:
        await setup_number(config, CONF_BOOST_TIME, var.set_boost_time, 1, 60, 1)
        await setup_sensor(config, CONF_BOOST_TIME_LEFT, var.set_boost_time_left)

    cg.add_build_flag("-DTION_ESPHOME")
    # cg.add_library("tion-api", None, "https://github.com/dentra/tion-api")

    return var


async def setup_tion_vport_ble(config):
    var = await vport.setup_vport_ble(config)
    cg.add(var.set_state_timeout(config[CONF_STATE_TIMEOUT]))
    return var
