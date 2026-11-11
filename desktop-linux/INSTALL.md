# Internet's Dream — Linux

```bash
cd internet-dream-linux/desktop-linux
./run.sh            # creates .venv, installs PyQt6 + dreamcore[google,telegram]
```

The `dream` CLI lands in `desktop-linux/.venv/bin/dream`:

```bash
dream serve                 # backend API on :8765
dream tg-login && dream tg-sync   # Telegram userbot (needs api_id/hash)
dream auth                  # Google OAuth (or use dashboard Connect button)
dream sync gmail|calendar|drive|photos|youtube|browser|files|telegram
```

Point the web dashboard / Android app / extension at `http://<this-host>:8765`.
