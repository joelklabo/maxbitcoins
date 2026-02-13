# MaxBitcoins

Autonomous Bitcoin-earning AI agent running on honkbox with Ollama for local LLM inference.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MaxBitcoins v2                           │
├─────────────────────────────────────────────────────────────┤
│   Python Brain (Docker on honkbox)                         │
│   • Agent loop (every 30 min)                              │
│   • Ollama for reasoning (local, free)                     │
│   • LNbits for wallet                                      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/joelklabo/maxbitcoins.git
cd maxbitcoins
cp .env.example .env
docker build -t maxbitcoins .
docker run -d --name maxbitcoins --restart unless-stopped -v ~/.satmax:/data --env-file .env maxbitcoins
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| LNURL | Your Lightning address |
| LNBITS_URL | LNbits instance URL |
| LNBITS_KEY | LNbits API key |
| OLLAMA_HOST | Ollama endpoint |

## License

MIT
