"""Configure a local SG5K-D inverter."""
import probatio as vol
from homeassistant.config_entries import ConfigFlow

from .client import SungrowError, read_snapshot
from .const import DOMAIN


class SungrowLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await read_snapshot(user_input["host"], smart_meter=user_input["smart_meter"])
            except (SungrowError, UnicodeError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(data["serial"])
                self._abort_if_unique_id_configured(updates={"host": user_input["host"]})
                if user_input["smart_meter"] and not data.get("meter_available"):
                    errors["base"] = "meter_unavailable"
                else:
                    return self.async_create_entry(title=user_input["name"], data={
                        **user_input, "serial": data["serial"],
                    })
        schema = vol.Schema({
            vol.Required("host"): str,
            vol.Required("name", default="Sungrow Inverter"): str,
            vol.Required("smart_meter", default=False): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        """Change the address or meter option while preserving inverter identity."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                snapshot = await read_snapshot(user_input["host"], smart_meter=user_input["smart_meter"])
            except (SungrowError, UnicodeError):
                errors["base"] = "cannot_connect"
            else:
                if snapshot["serial"] != entry.data["serial"]:
                    errors["base"] = "wrong_inverter"
                elif user_input["smart_meter"] and not snapshot.get("meter_available"):
                    errors["base"] = "meter_unavailable"
                else:
                    return self.async_update_reload_and_abort(
                        entry, title=user_input["name"], data_updates=user_input,
                    )
        return self.async_show_form(step_id="reconfigure", errors=errors, data_schema=vol.Schema({
            vol.Required("host", default=entry.data["host"]): str,
            vol.Required("name", default=entry.title): str,
            vol.Required("smart_meter", default=entry.data.get("smart_meter", False)): bool,
        }))
