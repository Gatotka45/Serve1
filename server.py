#!/usr/bin/env python3
"""
Pokemon Anil/Indigo Cable Club server - supports OLD and NEW plugin clients.
No dependencies. Run:  python3 server.py   (env: PORT, AUTO_PORT, NEW_MIN_VERSION, ALLOW_MIXED, ROOM_CODE)

OLD client expects: found,<cid>,<name>,<type>,<win>,<lose>,<party...>,0
NEW client expects: found,<cid>,<version>,<group>,<name>,<id>,<type>,<win>,<lose>,<party...>,0
Both send:          find,<version>,<group>,<name>,<id>,<type>,<win>,<lose>,<party...>
A client is "new" if its game version >= NEW_MIN_VERSION.
Listens on PORT (Railway sets it) in OLD format - use this for the "Servidor antiguo" switch in
PluginScripts and for real old-plugin clients. Optional AUTO_PORT adds a second port that
auto-detects old/new format by game version.
"""
import asyncio, os, re, time

OLD_PORT = int(os.environ.get("OLD_PORT") or os.environ.get("PORT") or 25566)
AUTO_PORT = int(os.environ.get("AUTO_PORT") or 0)
NEW_MIN_VERSION = os.environ.get("NEW_MIN_VERSION", "4.9")
ALLOW_MIXED = os.environ.get("ALLOW_MIXED", "0") == "1"   # old<->new pairing (party formats may differ)
ROOM_CODE = os.environ.get("ROOM_CODE")                    # optional: only this code accepted
HANDSHAKE_TIMEOUT = 20
MAX_HANDSHAKE = 512 * 1024

waiting = {}   # code -> Client
paired = {}    # code -> (Client, Client)


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)


def split_raw(line):
    """Split on unescaped commas, keeping the escaped text untouched."""
    out, cur, esc = [], [], False
    for ch in line:
        if ch == "," and not esc:
            out.append("".join(cur)); cur = []; esc = False
        else:
            cur.append(ch)
            esc = (ch == "\\") and not esc
    out.append("".join(cur))
    return out


class Client:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.raw = []
        self.code = None
        self.new = True
        self.partner = None

    def send(self, text):
        try:
            self.writer.write((text + "\n").encode("utf-8"))
        except Exception:
            pass

    def close(self):
        try:
            self.writer.close()
        except Exception:
            pass


def found_for(receiver, other, cid):
    r = other.raw
    if receiver.new:
        return "found,%d,%s,0" % (cid, ",".join(r[1:]))
    # old format: drop version, group, player id
    return "found,%d,%s,0" % (cid, ",".join([r[3], r[5], r[6], r[7]] + r[8:]))


async def handle(reader, writer, force_old=False):
    c = Client(reader, writer)
    peer = writer.get_extra_info("peername")
    try:
        try:
            data = b""
            while b"\n" not in data:
                chunk = await asyncio.wait_for(reader.read(65536), HANDSHAKE_TIMEOUT)
                if not chunk:
                    return
                data += chunk
                if len(data) > MAX_HANDSHAKE:
                    return
        except asyncio.TimeoutError:
            return
        line, _, rest = data.partition(b"\n")
        raw = split_raw(line.decode("utf-8", "replace").rstrip("\r"))
        if raw[0] != "find" or len(raw) < 9:
            return
        c.raw = raw
        version, code = raw[1], raw[2]
        c.code = code
        c.new = False if force_old else vtuple(version) >= vtuple(NEW_MIN_VERSION)
        print(time.strftime("%H:%M:%S"), peer, "find v=%s room=%s name=%s %s" %
              (version, code, raw[3], "NEW" if c.new else "OLD"), flush=True)

        if ROOM_CODE and code != ROOM_CODE:
            return c.send("disconnect,invalid code")
        if code in paired:
            return c.send("disconnect,group full")

        other = waiting.get(code)
        if other and other.writer.is_closing():
            waiting.pop(code, None); other = None
        if other:
            if other.new != c.new and not ALLOW_MIXED:
                return c.send("disconnect,invalid version")
            del waiting[code]
            paired[code] = (other, c)
            other.partner, c.partner = c, other
            other.send(found_for(other, c, 0))
            c.send(found_for(c, other, 1))
            print("  paired room", code, flush=True)
        else:
            waiting[code] = c

        if rest and c.partner:
            c.partner.writer.write(rest)
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                break
            if c.partner:
                c.partner.writer.write(chunk)
    except (ConnectionError, OSError):
        pass
    finally:
        if waiting.get(c.code) is c:
            del waiting[c.code]
        p = c.partner
        if p:
            paired.pop(c.code, None)
            p.partner = None
            p.send("disconnect,peer disconnected")
            p.close()
        c.close()


async def main():
    servers = [await asyncio.start_server(lambda r, w: handle(r, w, True), "0.0.0.0", OLD_PORT)]
    msg = "Cable Club server | OLD-format port %d" % OLD_PORT
    if AUTO_PORT and AUTO_PORT != OLD_PORT:
        servers.append(await asyncio.start_server(handle, "0.0.0.0", AUTO_PORT))
        msg += " | auto port %d (new if version >= %s, mixed: %s)" % (AUTO_PORT, NEW_MIN_VERSION, ALLOW_MIXED)
    print(msg, flush=True)
    await asyncio.gather(*(sv.serve_forever() for sv in servers))

if __name__ == "__main__":
    asyncio.run(main())
