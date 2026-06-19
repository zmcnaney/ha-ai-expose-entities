# AI Expose Entities

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

A Home Assistant integration that uses an AI Task (Claude, Gemini, GPT, or any other AI Task-capable conversation integration) to recommend which of your entities should be exposed to **Assist** — then lets you review and one-click approve those recommendations from a sidebar panel.

![Screenshot of the UI](docs/screenshot.png)

## What it does

- Builds a catalog of your Home Assistant entities (names, integration, device, disabled/hidden state).
- Sends a sample of that catalog to an AI Task you select during setup.
- Asks the AI to group related entities and explain why each group is worth exposing.
- Surfaces the result as **pending recommendations** in a sidebar panel.
- On approval, flips the Assist exposure flag for each entity via Home Assistant's standard exposure API.
- Remembers your approve/deny decisions so future runs only suggest new entities.

It does **not** itself call any third-party API. All AI calls go through Home Assistant's `ai_task.generate_data` service, so credentials, model choice, and quota all live with whichever conversation integration you point it at.

## Requirements

You need an `ai_task.*` entity already configured in Home Assistant. The dropdown in this integration's config flow is populated from those entities — if there are none, setup will abort with an explanation.

### Using it with Claude (recommended)

1. **Settings → Devices & Services → Add Integration → "Anthropic Conversation"**, paste your Anthropic API key (get one at <https://console.anthropic.com>).
2. On the Anthropic Conversation card, click **Configure → Add subentry → AI Task**. Pick a model:
   - **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — best cost/latency for this workload.
   - **Claude Sonnet 4.6** — sharper grouping/reasoning at higher cost.
3. Confirm an entity named `ai_task.<something>` now exists.
4. Add the **AI Expose Entities** integration. The AI Task dropdown will list your Claude AI Task.

### Using it with another provider

Any conversation integration that registers an AI Task entity will work — Google Generative AI, OpenAI Conversation, Ollama (with a recent enough version), etc. Set those up first and add an AI Task subentry, then add this integration.

## Model selection and cost

Each recommendation run sends one JSON-shaped catalog and asks for one JSON-shaped response — so model cost scales with how many entities you include per run (`Entities per run`, default 500). For large installs prefer fast/cheap models. Heavy reasoning models burn budget on a job that doesn't need them.

## Setup

1. Install via **HACS** (see button below) or copy `custom_components/ai_expose_entities/` into your `custom_components/` directory.
2. Restart Home Assistant.
3. Make sure you have an AI Task entity (see *Requirements*).
4. **Settings → Devices & Services → Add Integration → "AI Expose Entities"** (or use the My link below).
5. In the form, pick the AI Task, set **Entities per run**, and optionally turn on a custom prompt.

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zmcnaney&repository=ha-ai-expose-entities&category=integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ai_expose_entities)

## Daily use

A sidebar item titled **AI Expose Entities** is added on setup. Open it to:

- Pick an **aggressiveness**: minimal, gentle, balanced, bold, or **maximal** (most inclusive).
- Click **Run** — the integration sends the catalog to the AI Task and shows pending suggestions grouped by category, each with a short reason.
- Approve or deny suggestions. Approved entities are immediately exposed to Assist; denied entities are remembered and won't be suggested again.
- Optionally enable a **daily schedule** in the options flow so new entities get reviewed automatically.

## Configuration options

| Name | Where | What it does |
| -- | -- | -- |
| AI Task | Setup / Reconfigure | The `ai_task.*` entity used to generate recommendations. |
| Entities per run | Setup / Reconfigure | Cap on entities sent per call. If you have more, a random sample is used. |
| Use custom prompt | Setup / Reconfigure | If on, prepends your text to the built-in instructions. |
| Custom prompt | Setup / Reconfigure | Free-form text. Use `{entity_list}` to embed the JSON catalog yourself. |
| Enable daily recommendations | Options | Run automatically once a day. |
| Daily run time | Options | Local time of the daily run. |
| Enable debug logging | Options | Verbose logging — pair with the debug-logger config in *Troubleshooting* below. |

## Services

- `ai_expose_entities.run_recommendation` — trigger a recommendation pass on demand (use in automations).
- `ai_expose_entities.apply_decisions` — programmatically approve/deny entity IDs (`approved_entity_ids`, `denied_entity_ids`).

## Troubleshooting

### "No AI Task entities were found"

You don't have an `ai_task.*` entity yet. Follow the *Using it with Claude* section above (or set up another AI Task–capable integration), then re-run setup.

### Recommendations come back empty or fail to parse

The AI returned something that wasn't valid JSON. Switch to a stronger model temporarily, or enable debug logging and check what the AI actually returned:

```yaml
logger:
  default: info
  logs:
    custom_components.ai_expose_entities: debug
```

### I want it to consider *all* my entities, not a sample

Raise **Entities per run** to a number ≥ your entity count. The current upper bound is 2000.

## Contributing

Issues and PRs welcome. Local dev: open in VS Code with the Dev Containers extension, or use Codespaces:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/zmcnaney/ha-ai-expose-entities?quickstart=1)

## License

MIT — see [LICENSE](LICENSE).

---

> This integration was developed with assistance from AI coding agents. If you find rough edges or unexpected behavior, please [open an issue](../../issues).

[commits-shield]: https://img.shields.io/github/commit-activity/y/zmcnaney/ha-ai-expose-entities.svg?style=for-the-badge
[commits]: https://github.com/zmcnaney/ha-ai-expose-entities/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/zmcnaney/ha-ai-expose-entities.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40zmcnaney-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/zmcnaney/ha-ai-expose-entities.svg?style=for-the-badge
[releases]: https://github.com/zmcnaney/ha-ai-expose-entities/releases
