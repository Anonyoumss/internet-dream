# Internet's Dream — Qt6 Desktop Client

Material 3 Expressive desktop app — thin shell over `dream serve`.

## Features

- Dashboard: live memory stats + recent memories
- Search: hybrid search across your encrypted store
- Chat: agent chat (`POST /chat`) with visible tool steps
- Sources: per-source sync buttons + editable options
- Settings: API base URL, Google connect link, privacy notes
- Live connection chip in the status bar

## Build

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/internet-dream
```

Requires Qt6 (Widgets + Network): `apt install qt6-base-dev`.

## Headless smoke test

```bash
QT_QPA_PLATFORM=offscreen ./build/internet-dream --smoke
# exit 0 = connected to dream serve /health
```

## Layout

```
desktop-qt/
├── CMakeLists.txt
├── src/main.cpp          # entire app (Api client + 5 pages)
└── resources/
    ├── theme.qss         # Material 3 Expressive stylesheet
    └── resources.qrc
```
