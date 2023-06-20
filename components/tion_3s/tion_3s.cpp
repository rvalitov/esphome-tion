#include "esphome/core/log.h"

#include "tion_3s.h"

namespace esphome {
namespace tion {

static const char *const TAG = "tion_3s";

void Tion3s::dump_config() {
  this->dump_settings(TAG, "Tion 3S");
  LOG_SELECT("  ", "Air Intake", this->air_intake_);
}

void Tion3s::update_state() {
  const auto &state = this->state_;

  this->mode = !state.flags.power_state   ? climate::CLIMATE_MODE_OFF
               : state.flags.heater_state ? climate::CLIMATE_MODE_HEAT
                                          : climate::CLIMATE_MODE_FAN_ONLY;

  // heating detection borrowed from:
  // https://github.com/TionAPI/tion_python/blob/master/tion_btle/tion.py#L177
  bool is_heating = (state.target_temperature - state.outdoor_temperature) > 3 &&
                    state.current_temperature > state.outdoor_temperature;
  this->action = this->mode == climate::CLIMATE_MODE_OFF ? climate::CLIMATE_ACTION_OFF
                 : is_heating                            ? climate::CLIMATE_ACTION_HEATING
                                                         : climate::CLIMATE_ACTION_FAN;

  this->current_temperature = state.current_temperature;
  this->target_temperature = state.target_temperature;
  this->set_fan_speed_(state.fan_speed);
  this->publish_state();

  if (this->version_ && state.firmware_version > 0) {
    this->version_->publish_state(str_snprintf("%04X", 4, state.firmware_version));
  }
  if (this->buzzer_) {
    this->buzzer_->publish_state(state.flags.sound_state);
  }
  if (this->outdoor_temperature_) {
    this->outdoor_temperature_->publish_state(state.outdoor_temperature);
  }
  if (this->filter_time_left_) {
    this->filter_time_left_->publish_state(state.filter_time);
  }
  if (this->air_intake_) {
    auto air_intake = this->air_intake_->at(state.gate_position);
    if (air_intake.has_value()) {
      this->air_intake_->publish_state(*air_intake);
    }
  }
  if (this->airflow_counter_) {
    this->airflow_counter_->publish_state(state.productivity);
  }

  // additional request after state response
  if (this->vport_type_ == TionVPortType::VPORT_UART && this->state_.firmware_version < 0x003C) {
    // call on next loop
    this->defer([this]() { this->api_->request_after_state(); });
  }
}

void Tion3s::dump_state() const {
  const auto &state = this->state_;
  ESP_LOGV(TAG, "fan_speed    : %u", state.fan_speed);
  ESP_LOGV(TAG, "gate_position: %u", state.gate_position);
  ESP_LOGV(TAG, "target_temp  : %u", state.target_temperature);
  ESP_LOGV(TAG, "heater_state : %s", ONOFF(state.flags.heater_state));
  ESP_LOGV(TAG, "power_state  : %s", ONOFF(state.flags.power_state));
  ESP_LOGV(TAG, "timer_state  : %s", ONOFF(state.flags.timer_state));
  ESP_LOGV(TAG, "sound_state  : %s", ONOFF(state.flags.sound_state));
  ESP_LOGV(TAG, "auto_state   : %s", ONOFF(state.flags.auto_state));
  ESP_LOGV(TAG, "ma_connect   : %s", ONOFF(state.flags.ma_connect));
  ESP_LOGV(TAG, "save         : %s", ONOFF(state.flags.save));
  ESP_LOGV(TAG, "ma_pairing   : %s", ONOFF(state.flags.ma_pairing));
  ESP_LOGV(TAG, "reserved     : 0x%02X", state.flags.reserved);
  ESP_LOGV(TAG, "unknown_temp : %d", state.unknown_temperature);
  ESP_LOGV(TAG, "outdoor_temp : %d", state.outdoor_temperature);
  ESP_LOGV(TAG, "current_temp : %d", state.current_temperature);
  ESP_LOGV(TAG, "filter_time  : %u", state.filter_time);
  ESP_LOGV(TAG, "hours        : %u", state.hours);
  ESP_LOGV(TAG, "minutes      : %u", state.minutes);
  ESP_LOGV(TAG, "last_error   : %u", state.last_error);
  ESP_LOGV(TAG, "productivity : %u", state.productivity);
  ESP_LOGV(TAG, "filter_days  : %u", state.filter_days);
  ESP_LOGV(TAG, "firmware     : %04X", state.firmware_version);
}

void Tion3s::control_state(climate::ClimateMode mode, uint8_t fan_speed, int8_t target_temperature, bool buzzer,
                           uint8_t gate_position) const {
  tion3s_state_t st = this->state_;

  st.flags.power_state = this->mode != climate::CLIMATE_MODE_OFF;
  if (this->state_.flags.power_state != st.flags.power_state) {
    ESP_LOGD(TAG, "New power state %s", ONOFF(st.flags.power_state));
  }

  st.fan_speed = fan_speed;
  if (this->state_.fan_speed != fan_speed) {
    ESP_LOGD(TAG, "New fan speed %u", st.fan_speed);
  }

  st.target_temperature = target_temperature;
  if (this->state_.target_temperature != st.target_temperature) {
    ESP_LOGD(TAG, "New target temperature %d", target_temperature);
  }

  st.flags.sound_state = buzzer;
  if (this->state_.flags.sound_state != st.flags.sound_state) {
    ESP_LOGD(TAG, "New sound state %s", ONOFF(st.flags.sound_state));
  }

  st.gate_position = gate_position;
  if (this->state_.gate_position != st.gate_position) {
    ESP_LOGD(TAG, "New gate position %u", st.gate_position);
  }

  st.flags.heater_state = this->mode == climate::CLIMATE_MODE_HEAT;
  if (this->state_.flags.heater_state != st.flags.heater_state) {
    ESP_LOGD(TAG, "New heater state %s", ONOFF(st.flags.heater_state));

    // режим вентиляция изменить на обогрев можно только через выключение
    if (this->state_.flags.power_state && !this->state_.flags.heater_state && st.flags.heater_state) {
      st.flags.power_state = false;
      this->api_->write_state(st);
      st.flags.power_state = true;
    }
  }

  this->api_->write_state(st);
}

}  // namespace tion
}  // namespace esphome
