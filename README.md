# Pokemon Anil/Indigo Cable Club server

Online PvP/trade relay for the Cable Club plugin ("Servidor antiguo / Old server" option).
Pure Python 3, no dependencies.

## Deploy on Railway
1. Put these files in a GitHub repo.
2. Railway -> New Project -> Deploy from GitHub repo.
3. Service -> Variables: add `PORT` = `25566`.
4. Service -> Settings -> Networking -> **TCP Proxy** -> internal port `25566`.
   Railway shows `something.proxy.rlwy.net:12345`.
5. In the game folder, `Data/serverinfo.ini`:
   ```
   OLD_HOST=something.proxy.rlwy.net
   OLD_PORT=12345
   ```
6. In game: Cable Club -> "Servidor antiguo (Old server)" -> room code (same 8 digits on both phones).

## Variables
- `PORT` / `OLD_PORT`: listen port, old format (default 25566)
- `AUTO_PORT`: optional extra port, old/new format by game version
- `NEW_MIN_VERSION` (default 4.9), `ALLOW_MIXED=1`, `ROOM_CODE` (only that code allowed)

Logs show each connection (game version, room, name).
`data_for_showdown/` = name lists from the game (not used by the server).
