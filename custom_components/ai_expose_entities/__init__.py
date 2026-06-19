"""
Custom integration to integrate ai_expose_entities with Home Assistant.

This integration demonstrates best practices for:
- Config flow setup (user, reconfigure, reauth)
- DataUpdateCoordinator pattern for efficient data fetching
- Multiple platform types (sensor, binary_sensor, switch, select, number)
- Service registration and handling
- Device and entity management
- Proper error handling and recovery

For more details about this integration, please refer to:
https://github.com/zmcnaney/ha-ai-expose-entities

For integration development guidelines:
https://developers.home-assistant.io/docs/creating_integration_manifest
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_loaded_integration

from .api import AIExposeEntitiesAIClient
from .const import (
    CONF_AGENT_ID,
    CONF_CUSTOM_PROMPT,
    CONF_CUSTOM_PROMPT_ENABLED,
    CONF_ENABLE_DEBUGGING,
    CONF_TEST_ENTITIES,
    CONF_TEST_ENTITIES_ENABLED,
    CONF_TEST_ENTITY_COUNT,
    CONF_TEST_ENTITY_RELEVANT_COUNT,
    CONF_TEST_ENTITY_SEED,
    DEFAULT_CUSTOM_PROMPT,
    DEFAULT_CUSTOM_PROMPT_ENABLED,
    DEFAULT_ENABLE_DEBUGGING,
    DEFAULT_TEST_ENTITIES_ENABLED,
    DEFAULT_TEST_ENTITY_COUNT,
    DEFAULT_TEST_ENTITY_RELEVANT_COUNT,
    DEFAULT_TEST_ENTITY_SEED,
    DOMAIN,
    LOGGER,
)
from .coordinator import AIExposeEntitiesDataUpdateCoordinator
from .data import AIExposeEntitiesData
from .panel import async_register_panel
from .service_actions import async_setup_services
from .utils import (
    AIExposeEntitiesRecommendationStore,
    async_schedule_daily_run,
    build_test_entity_set,
    get_schedule_settings,
    parse_test_entity_config,
)
from .websocket import async_register_websocket

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import AIExposeEntitiesConfigEntry

TEST_ENTITIES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TEST_ENTITIES_ENABLED, default=DEFAULT_TEST_ENTITIES_ENABLED): cv.boolean,
        vol.Optional(CONF_TEST_ENTITY_COUNT, default=DEFAULT_TEST_ENTITY_COUNT): vol.All(
            vol.Coerce(int),
            vol.Range(min=0),
        ),
        vol.Optional(CONF_TEST_ENTITY_RELEVANT_COUNT, default=DEFAULT_TEST_ENTITY_RELEVANT_COUNT): vol.All(
            vol.Coerce(int),
            vol.Range(min=0),
        ),
        vol.Optional(CONF_TEST_ENTITY_SEED, default=DEFAULT_TEST_ENTITY_SEED): vol.All(
            vol.Coerce(int),
            vol.Range(min=0),
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(CONF_TEST_ENTITIES, default={}): TEST_ENTITIES_SCHEMA,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the integration.

    This is called once at Home Assistant startup to register service actions.
    Service actions must be registered here (not in async_setup_entry) to ensure:
    - Service action validation works correctly
    - Service actions are available even without config entries
    - Helpful error messages are provided

    This is a Silver Quality Scale requirement.

    Args:
        hass: The Home Assistant instance.
        config: The Home Assistant configuration.

    Returns:
        True if setup was successful.

    For more information:
    https://developers.home-assistant.io/docs/dev_101_services
    """
    await async_setup_services(hass)
    test_config = parse_test_entity_config(config.get(DOMAIN, {}).get(CONF_TEST_ENTITIES))
    hass.data.setdefault(DOMAIN, {})[CONF_TEST_ENTITIES] = test_config
    async_register_websocket(hass)
    await async_register_panel(hass)
    LOGGER.debug("Integration setup complete")
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AIExposeEntitiesConfigEntry,
) -> bool:
    """
    Set up this integration using UI.

    This is called when a config entry is loaded. It:
    1. Initializes the AI client based on selected AI Task entity
    2. Loads recommendation state from storage
    3. Initializes the DataUpdateCoordinator for state updates
    4. Performs the first state refresh
    5. Registers schedule listeners for automated recommendations
    6. Sets up reload listener for config changes

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.

    Returns:
        True if setup was successful.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
    """
    debug_enabled = bool(entry.options.get(CONF_ENABLE_DEBUGGING, DEFAULT_ENABLE_DEBUGGING))
    agent_id = entry.options.get(CONF_AGENT_ID)
    if debug_enabled:
        LOGGER.debug(
            "Setting up config entry %s with agent_id=%s",
            entry.entry_id,
            agent_id,
        )
    custom_prompt_enabled = bool(entry.options.get(CONF_CUSTOM_PROMPT_ENABLED, DEFAULT_CUSTOM_PROMPT_ENABLED))
    custom_prompt = entry.options.get(CONF_CUSTOM_PROMPT, DEFAULT_CUSTOM_PROMPT)
    client = AIExposeEntitiesAIClient(
        hass,
        agent_id,
        custom_prompt=custom_prompt,
        custom_prompt_enabled=custom_prompt_enabled,
        debug_enabled=debug_enabled,
    )

    store = AIExposeEntitiesRecommendationStore(hass, entry.entry_id, debug_enabled=debug_enabled)
    state = await store.async_load()

    # Initialize coordinator with config_entry
    coordinator = AIExposeEntitiesDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        config_entry=entry,
        update_interval=None,
        always_update=True,
    )

    test_config = hass.data.get(DOMAIN, {}).get(CONF_TEST_ENTITIES)
    test_entities = build_test_entity_set(test_config) if test_config else None
    if test_entities:
        coordinator.set_entity_data(test_entities.data)
    else:
        coordinator.set_entity_data({"model": "AI Expose Entities", "userId": 1, "id": 1})

    platforms: list[Platform] = []
    if test_entities:
        platforms.append(Platform.SENSOR)

    # Store runtime data
    entry.runtime_data = AIExposeEntitiesData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        platforms=platforms,
        store=store,
        state=state,
        test_entities=test_entities,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()
    if debug_enabled:
        LOGGER.debug("Initial coordinator refresh complete for %s", entry.entry_id)

    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    entry.async_on_unload(_async_register_schedule(hass, entry, coordinator))

    if debug_enabled:
        LOGGER.debug("Config entry %s setup complete", entry.entry_id)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AIExposeEntitiesConfigEntry,
) -> bool:
    """
    Unload a config entry.

    This is called when the integration is being removed or reloaded.
    It ensures proper cleanup of:
    - All platform entities
    - Registered services
    - Update listeners

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being unloaded.

    Returns:
        True if unload was successful.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#unloading-entries
    """
    platforms = entry.runtime_data.platforms
    if platforms:
        result = await hass.config_entries.async_unload_platforms(entry, platforms)
        if entry.options.get(CONF_ENABLE_DEBUGGING, DEFAULT_ENABLE_DEBUGGING):
            LOGGER.debug("Config entry %s unload result: %s", entry.entry_id, result)
        return result
    if entry.options.get(CONF_ENABLE_DEBUGGING, DEFAULT_ENABLE_DEBUGGING):
        LOGGER.debug("Config entry %s unloaded (no platforms)", entry.entry_id)
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: AIExposeEntitiesConfigEntry,
) -> None:
    """
    Reload config entry.

    This is called when the integration configuration or options have changed.
    It unloads and then reloads the integration with the new configuration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being reloaded.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#reloading-entries
    """
    if entry.options.get(CONF_ENABLE_DEBUGGING, DEFAULT_ENABLE_DEBUGGING):
        LOGGER.debug("Reloading config entry %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_schedule(
    hass: HomeAssistant,
    entry: AIExposeEntitiesConfigEntry,
    coordinator: AIExposeEntitiesDataUpdateCoordinator,
):
    """Register the daily recommendation schedule."""
    settings = get_schedule_settings(entry.options)
    if entry.options.get(CONF_ENABLE_DEBUGGING, DEFAULT_ENABLE_DEBUGGING):
        LOGGER.debug(
            "Schedule settings for %s: enabled=%s time=%02d:%02d",
            entry.entry_id,
            settings.enabled,
            settings.hour,
            settings.minute,
        )
    unsubscribe = async_schedule_daily_run(hass, coordinator, settings)
    if unsubscribe is None:
        return lambda: None
    return unsubscribe
