# nepremicninko
A web crawler for Nepremicnine.net. 
This is an unofficial fork of [nepremicnine-discord-bot](https://github.com/mevljas/nepremicnine-discord-bot), I wanted to make a simpler version.

## Disclaimer ⚠️

This is an unofficial tool and is not affiliated with Nepremicnine.net. Please use responsibly and respect their terms of service.

## Configuration

You need to set up a config file `config.yaml` in project root.
An `config.example.yaml` file is provided, all you need to do is input your Discord webhook, 
everything else has reasonable defaults.


Fill out the `urls:` field and define your search parameters.
You can use multiple URLs, each in a new line

Example url: 
```yaml
urls:
  # Rent
  - https://www.nepremicnine.net/oglasi-oddaja/ljubljana-mesto/stanovanje/1-sobno,2-sobno/cena-do-600-eur-na-mesec
  # Purchase
  - https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/1-sobno,2-sobno/
```

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

Run the app
```bash
python -m main
```

## Logging

The app uses structured JSON logs to monitor operation. You can access them via `./logs`.