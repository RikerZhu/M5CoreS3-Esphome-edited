import esphome.config_validation as cv
import esphome.final_validate as fv
import esphome.codegen as cg

from esphome import pins
from esphome.const import CONF_ID, CONF_MICROPHONE, CONF_SPEAKER
from esphome.components.esp32 import get_esp32_variant
from esphome.components.esp32.const import (
    VARIANT_ESP32,
    VARIANT_ESP32S2,
    VARIANT_ESP32S3,
    VARIANT_ESP32C3,
)

CODEOWNERS = ["@jesserockz"]
DEPENDENCIES = ["esp32"]
MULTI_CONF = True

CONF_I2S_DOUT_PIN = "i2s_dout_pin"
CONF_I2S_DIN_PIN = "i2s_din_pin"
CONF_I2S_MCLK_PIN = "i2s_mclk_pin"
CONF_I2S_BCLK_PIN = "i2s_bclk_pin"
CONF_I2S_LRCLK_PIN = "i2s_lrclk_pin"

CONF_I2S_AUDIO = "m5cores3_audio"
CONF_I2S_AUDIO_ID = "m5cores3_audio_id"

i2s_audio_ns = cg.esphome_ns.namespace("m5cores3_audio")
I2SAudioComponent = i2s_audio_ns.class_("M5CoreS3AudioComponent", cg.Component)
I2SAudioIn = i2s_audio_ns.class_("I2SAudioIn", cg.Parented.template(I2SAudioComponent))
I2SAudioOut = i2s_audio_ns.class_(
    "I2SAudioOut", cg.Parented.template(I2SAudioComponent)
)

# https://github.com/espressif/esp-idf/blob/master/components/soc/{variant}/include/soc/soc_caps.h
I2S_PORTS = {
    VARIANT_ESP32: 2,
    VARIANT_ESP32S2: 1,
    VARIANT_ESP32S3: 2,
    VARIANT_ESP32C3: 1,
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(I2SAudioComponent),
        cv.Optional(CONF_I2S_LRCLK_PIN): pins.internal_gpio_output_pin_number,
        cv.Optional(CONF_I2S_BCLK_PIN): pins.internal_gpio_output_pin_number,
        cv.Optional(CONF_I2S_MCLK_PIN): pins.internal_gpio_output_pin_number,
    }
)


def _final_validate(_):
    inject_max_channels()
    
    i2s_audio_configs = fv.full_config.get()[CONF_I2S_AUDIO]
    variant = get_esp32_variant()
    if variant not in I2S_PORTS:
        raise cv.Invalid(f"Unsupported variant {variant}")
    if len(i2s_audio_configs) > I2S_PORTS[variant]:
        raise cv.Invalid(
            f"Only {I2S_PORTS[variant]} I2S audio ports are supported on {variant}"
        )


FINAL_VALIDATE_SCHEMA = _final_validate

def inject_max_channels():
    config = fv.full_config.get()
    for section in (CONF_MICROPHONE, CONF_SPEAKER):
        items = config.get(section, [])
        for item in items:
            if item.get("platform") == "m5cores3_audio":
                item["max_channels"] = 1

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # cg.add(var.set_lrclk_pin(config[CONF_I2S_LRCLK_PIN]))
    if CONF_I2S_LRCLK_PIN in config:
        cg.add(var.set_bclk_pin(config[CONF_I2S_LRCLK_PIN]))
    if CONF_I2S_BCLK_PIN in config:
        cg.add(var.set_bclk_pin(config[CONF_I2S_BCLK_PIN]))
    if CONF_I2S_MCLK_PIN in config:
        cg.add(var.set_mclk_pin(config[CONF_I2S_MCLK_PIN]))

# --- Add compatibility fix for ESPHome 2025.7+ audio schema ---
try:
    import esphome.components.audio as audio
    from esphome.const import CONF_MAX_CHANNELS
    import voluptuous as vol

    # patch audio.CONFIG_SCHEMA if not already patched
    audio.CONFIG_SCHEMA = audio.CONFIG_SCHEMA.extend({
        vol.Optional(CONF_MAX_CHANNELS, default=1): cv.positive_int,
    })

    # patch final validator if needed
    original_validate = audio.validate_audio_compatiblity

    def patched_validate_audio_compatiblity(config):
        if CONF_MAX_CHANNELS not in config or config[CONF_MAX_CHANNELS] is None:
            config[CONF_MAX_CHANNELS] = 1
        return original_validate(config)

    audio.validate_audio_compatiblity = patched_validate_audio_compatiblity

except Exception as e:
    # Optional debug log
    pass
