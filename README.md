# nepremicninko
A web crawler for Nepremicnine.net. 
This is an unofficial fork of [nepremicnine-discord-bot](https://github.com/mevljas/nepremicnine-discord-bot), I wanted to make a simpler version.

## Disclaimer ⚠️

This is an unofficial tool and is not affiliated with Nepremicnine.net. Please use responsibly and respect their terms of service.

## Setup

You need to set up the environment variables. An `.env.example` is provided, all you need to do is provide your Discord webhook, everything else should work from the box.

### How to access Discords webhook URL

- You need access to a Discord server where you are at least admin or higher.
- The Webhook URL can be generated via settings:
  - `Server settings -> Integrations -> Webhooks -> New Webhook`
- Select a chanel and name the hook.
- Once you get the URL, paste it in your: `.env` under `DISCORD_WEBHOOK_URL`:

## Docker

You can run the app locally, but the easiest way is with Docker.
Run the scrapper with this command:

```bash
   docker compose -f ./deployment/docker-compose.yml -p nepremicninko up
```

## Local
If you want to run nepremicninko locally for development:

```bash
   uv sync
```

Install Playwright browsers

```bash
   uv run playwright install chromium
```

## Configuration

Access `./config/urls.txt` and define your search parameters.

## Logging

The app uses structured JSON logs to monitor operation. You can access them via `./logs`.