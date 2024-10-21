"""Support for MyHome heating."""

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    DOMAIN as PLATFORM,
)

from homeassistant.const import (
    CONF_NAME,
    CONF_MAC
)


from .message import (
    OWNAudioCommand,
    OWNAudioEvent,
    MESSAGE_TYPE_AUDIO_VOLUME,
    MESSAGE_TYPE_AUDIO_STATE,
    MESSAGE_TYPE_AUDIO_STATION
)

from .const import (
    CONF_PLATFORMS,
    CONF_ENTITY,
    CONF_WHO,
    CONF_WHERE,
    CONF_MANUFACTURER,
    CONF_DEVICE_MODEL,
    DOMAIN,
    LOGGER,
)

from .myhome_device import MyHOMEEntity
from .gateway import MyHOMEGatewayHandler

async def async_setup_entry(hass, config_entry, async_add_entities):
    if PLATFORM not in hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS]:
        return True

    _media_player_devices = []
    _configured_media_player_devices = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS][PLATFORM]

    for _media_player_device in _configured_media_player_devices.keys():
        _media_player_devices.append(
            MyHOMEMediaPlayer(
                hass=hass,
                device_id=_media_player_device,
                who=_configured_media_player_devices[_media_player_device][CONF_WHO],
                where=_configured_media_player_devices[_media_player_device][CONF_WHERE],
                name=_configured_media_player_devices[_media_player_device][CONF_NAME],
                manufacturer=_configured_media_player_devices[_media_player_device][CONF_MANUFACTURER],
                model=_configured_media_player_devices[_media_player_device][CONF_DEVICE_MODEL],
                gateway=hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY],
            )
        )

    async_add_entities(_media_player_devices)


async def async_unload_entry(hass, config_entry):
    if PLATFORM not in hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS]:
        return True

    _configured_media_player_devices = hass.data[DOMAIN][config_entry.data[CONF_MAC]][
        CONF_PLATFORMS
    ][PLATFORM]

    for _media_player_device in _configured_media_player_devices.keys():
        del hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS][PLATFORM][
            _media_player_device
        ]


class MyHOMEMediaPlayer(MyHOMEEntity, MediaPlayerEntity):
    def __init__(
        self,
        hass,
        name: str,
        device_id: str,
        who: str,
        where: str,
        manufacturer: str,
        model: str,
        gateway: MyHOMEGatewayHandler,
    ):
        super().__init__(
            hass=hass,
            name=name,
            platform=PLATFORM,
            device_id=device_id,
            who=who,
            where=where,
            manufacturer=manufacturer,
            model=model,
            gateway=gateway,
        )
        
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.NEXT_TRACK
        )
        self._state = MediaPlayerState.OFF
        self._attr_volume_level = 0.5
        self.active_source = "Radio"
        self._station = "Unknown Title"
        
    @property
    def media_content_type(self) -> MediaType | None:
        return MediaType.MUSIC;

    @property
    def source(self) -> str | None:
        return self.active_source
        
    @property
    def source_list(self) -> list[str]:
        return ["Radio", "Stream"]

    @property
    def state(self) -> MediaPlayerState:
        return self._state
  
    @property
    def media_channel(self) -> str | None:
        return "Unknown Channel"

    @property
    def media_title(self) -> str | None:
        return self._station

    async def async_update(self):
        await self._gateway_handler.send_status_request(OWNAudioCommand.status(where=self._where))
        self.schedule_update_ha_state()

    async def async_select_source(self, source: str) -> None:
        self.active_source = source
        await self._gateway_handler.send(OWNAudioCommand.select_source(where=self._where, src=source))
        self.schedule_update_ha_state()

    async def async_media_next_track(self) -> None:
        await self._gateway_handler.send(OWNAudioCommand.next_track(where=self._where))
        self.schedule_update_ha_state()

    async def async_media_previous_track(self) -> None:
        await self._gateway_handler.send(OWNAudioCommand.prev_track(where=self._where))
        self.schedule_update_ha_state()
        
    async def async_set_volume_level(self, volume: float) -> None:
        await self._gateway_handler.send(OWNAudioCommand.volume_set(where=self._where, vol=volume))
        self.schedule_update_ha_state()

    async def async_volume_up(self) -> None:
        await self._gateway_handler.send(OWNAudioCommand.volume_up(where=self._where))
        self.schedule_update_ha_state()

    async def async_volume_down(self) -> None:
        await self._gateway_handler.send(OWNAudioCommand.volume_down(where=self._where))
        self.schedule_update_ha_state()
        
    async def async_media_play(self):
        await self._gateway_handler.send(OWNAudioCommand.play(where=self._where))
        self.schedule_update_ha_state()
   
    async def async_turn_on(self):
        await self._gateway_handler.send(OWNAudioCommand.play(where=self._where))
        self.schedule_update_ha_state()

    async def async_turn_off(self):
        await self._gateway_handler.send(OWNAudioCommand.stop(where=self._where))
        self.schedule_update_ha_state()  
   
    async def async_media_stop(self):
        await self._gateway_handler.send(OWNAudioCommand.stop(where=self._where))
        self.schedule_update_ha_state()  
        
    def handle_event(self, message: OWNAudioEvent):
        if message.message_type == MESSAGE_TYPE_AUDIO_STATION:
            self._station = message.station
        if message.message_type == MESSAGE_TYPE_AUDIO_VOLUME:
            if message.volume == 0:
                self._attr_volume_level = 0
            else:
                self._attr_volume_level = 1.0 / 31.0 * float(message.volume)
        if message.message_type == MESSAGE_TYPE_AUDIO_STATE:
            if message.state == 0:
                self._state = MediaPlayerState.OFF
            else:
                self._state = MediaPlayerState.PLAYING

        self.async_schedule_update_ha_state()    
