# ha-blueprints

Blueprints to use with Home Assistant.

| Blueprint | What it does |
|---|---|
| [conditional-close-blinds.yaml](conditional-close-blinds.yaml) | Close blinds based on conditions |
| [motion-activated-lights-time-of-day.yaml](motion-activated-lights-time-of-day.yaml) | Motion-activated lights with time-of-day brightness and hold |
| [shelly-blu-remote-control-zb-zha.yaml](shelly-blu-remote-control-zb-zha.yaml) | Shelly BLU Remote Control ZB over Zigbee (ZHA): ring buttons and wheel on all 4 channels. Needs the quirk below. |
| [shelly-blu-remote-control-zb-bthome.yaml](shelly-blu-remote-control-zb-bthome.yaml) | Same remote over Bluetooth (BTHome), no quirk needed. |

## Custom ZHA quirks

- [custom_zha_quirks/shelly_blu_remote_zb.py](custom_zha_quirks/shelly_blu_remote_zb.py) – adds the selected channel to the Shelly BLU Remote Control ZB's ZHA events (`left_press`, `right_press`, `wheel_up`, `wheel_down`). Copy it into the folder set as `zha: custom_quirks_path:` in `configuration.yaml` and restart Home Assistant. Tested on remote firmware v1.2.13.
