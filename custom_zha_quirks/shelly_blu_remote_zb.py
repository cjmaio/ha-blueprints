"""Shelly BLU Remote Control ZB: channel-aware button and wheel events for ZHA.

The remote group-casts its standard On/Off and Level Control commands to the
group matching the selected channel (group 0-3 = LED 1-4). ZHA drops the group
address, so this quirk reads it from each incoming frame and fires extra
zha_events that include the channel:

    left_press / right_press         args: {"channel": 1-4}
    wheel_up / wheel_down            args: {"channel": 1-4, "step_size": 0-255, "steps": notches}

Firmware v1.2.13 sends custom commands that carry the channel explicitly
instead (On/Off 0x80/0x81, Level Control 0x86); those are decoded too.

https://shelly-api-docs.shelly.cloud/docs-ble/Devices/BLU_ZB/blu_remote
"""

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff, StepMode
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import ZHA_SEND_EVENT
from zhaquirks.device import CustomZigpyDevice


class ShellyRemoteDevice(CustomZigpyDevice):
    """Remembers the group address of the frame being processed."""

    last_group: int | None = None

    def packet_received(self, packet: t.ZigbeePacket) -> None:
        """Note the destination group, then process the packet as usual."""
        dst = packet.dst
        self.last_group = dst.address if dst is not None and dst.addr_mode == t.AddrMode.Group else None
        super().packet_received(packet)


def _channel(cluster: CustomCluster, explicit: int | None = None) -> int | None:
    """Return the channel as the LED number (1-4)."""
    if explicit is not None:
        return explicit + 1
    group = getattr(cluster.endpoint.device, "last_group", None)
    return group + 1 if group is not None and group < 4 else None


class ShellyRemoteOnOff(CustomCluster, OnOff):
    """On/Off client cluster: left ring sends on, right ring sends off."""

    class ServerCommandDefs(OnOff.ServerCommandDefs):
        """Server command definitions."""

        off_with_channel: Final = ZCLCommandDef(id=0x80, schema={"channel": t.uint8_t}, manufacturer_code=None)
        on_with_channel: Final = ZCLCommandDef(id=0x81, schema={"channel": t.uint8_t}, manufacturer_code=None)
        toggle_with_channel: Final = ZCLCommandDef(id=0x82, schema={"channel": t.uint8_t}, manufacturer_code=None)

    _BUTTONS = {0x00: "right_press", 0x01: "left_press", 0x80: "right_press", 0x81: "left_press"}

    def handle_cluster_request(self, hdr: foundation.ZCLHeader, args: Any, *, dst_addressing=None):
        """Fire a channel-aware event, then handle the command as usual."""
        event = self._BUTTONS.get(hdr.command_id)
        if event is not None:
            explicit = args.channel if hdr.command_id >= 0x80 else None
            self.listener_event(ZHA_SEND_EVENT, event, {"channel": _channel(self, explicit)})
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class ShellyRemoteLevelControl(CustomCluster, LevelControl):
    """Level Control client cluster: the wheel sends step commands."""

    class ServerCommandDefs(LevelControl.ServerCommandDefs):
        """Server command definitions."""

        # Documented as 0x80, but firmware v1.2.13 sends 0x86 (manufacturer 0x1490).
        step_with_channel: Final = ZCLCommandDef(
            id=0x86,
            schema={
                "step_mode": StepMode,
                "step_size": t.uint8_t,
                "transition_time": t.uint16_t,
                "channel": t.uint8_t,
            },
            manufacturer_code=None,
        )

    def handle_cluster_request(self, hdr: foundation.ZCLHeader, args: Any, *, dst_addressing=None):
        """Fire a channel-aware event, then handle the command as usual."""
        cmd = self.server_commands.get(hdr.command_id)
        if cmd is not None and cmd.name in ("step", "step_with_on_off", "step_with_channel"):
            explicit = args.channel if hdr.command_id == 0x86 else None
            self.listener_event(
                ZHA_SEND_EVENT,
                "wheel_up" if args.step_mode == StepMode.Up else "wheel_down",
                {
                    "channel": _channel(self, explicit),
                    "step_size": int(args.step_size),
                    # The remote sends 3 brightness units per wheel notch.
                    "steps": int(args.step_size) // 3,
                },
            )
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder("Shelly", "BLU Remote Control ZB")
    .device_class(ShellyRemoteDevice)
    .replaces(ShellyRemoteOnOff, cluster_type=ClusterType.Client)
    .replaces(ShellyRemoteLevelControl, cluster_type=ClusterType.Client)
    .add_to_registry()
)
