#!/usr/bin/env python3
"""Capture et analyse des trames de la télécommande EasyWorship.

Bibliothèque standard uniquement (Python >= 3.8, macOS / Windows / Linux).
Lecture seule : le script se présente comme une télécommande, écoute, et
n'envoie que les requêtes de lecture utilisées par ew2vm (GetLiveData,
getSlideInfo) et les heartbeats.

Usage :
    python tools/ew_capture.py NOM_OU_IP_DU_PC_EW            capture 60 s
    python tools/ew_capture.py PC-REGIE --duration 300       capture 5 min
    python tools/ew_capture.py PC-REGIE --port 51234         port connu (sans mDNS)
    python tools/ew_capture.py PC-REGIE --passive            n'envoie que heartbeat
    python tools/ew_capture.py PC-REGIE --redact             masque titres et textes
    python tools/ew_capture.py --analyze captures/xxx.jsonl  analyse un fichier
    python tools/ew_capture.py --selftest                    test avec un faux EW

Pendant la capture : changez de diapo, passez en logo / noir / clear, changez
de présentation. Les fichiers (captures/*.jsonl) contiennent le texte des
diapos : ne pas les publier tels quels (voir --redact).
"""
import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime

MDNS_PORT = 5353
MDNS_SERVICE = "_ezwremote._tcp.local"
# Identité de la V1 (src_v1/ew_api.py) : EW connaît peut-être déjà cette télécommande.
V1_CLIENT_ID = "a164e834-fc66-4cff-8e47-aa904ee9e62b"
V1_DEVICE_NAME = "ew to obs"
EXTRA_ACTIONS = {"LiveData", "ScheduleData", "currentImage", "slideImage"}
IMAGE_ACTIONS = {"currentImage", "slideImage"}
KNOWN_SENT = {"connect", "heartbeat", "GetLiveData", "getSlideInfo"}
KNOWN_RECV = {"paired", "notPaired", "status", "LiveData", "slideInfo", "ScheduleData", "currentImage", "slideImage"}
REDACT_KEYS = {"title", "content", "device_name"}
LIVEDATA_HEADER = struct.Struct("<lqqqlq")  # 40 octets, voir doc/protocole_easyworship.md
LIVEDATA_SLIDE = struct.Struct("<qq")  # rowid, revision
HEARTBEAT_EVERY = 3.0


###################################################################################################
##  mDNS : découverte du port TCP (requête unicast, comme ew_api.py)                             ##
###################################################################################################
def _encode_name(name):
    out = b""
    for label in name.strip(".").split("."):
        raw = label.encode("utf-8")
        out += bytes([len(raw)]) + raw
    return out + b"\0"


def _read_name(data, pos):
    """Lit un nom DNS (avec compression). Renvoie (nom, position après le nom)."""
    labels, end, hops = [], None, 0
    while True:
        if pos >= len(data):
            raise ValueError("nom DNS tronqué")
        n = data[pos]
        if n == 0:
            pos += 1
            break
        if n & 0xC0 == 0xC0:
            if end is None:
                end = pos + 2
            pos = ((n & 0x3F) << 8) | data[pos + 1]
            hops += 1
            if hops > 20:
                raise ValueError("boucle de compression DNS")
            continue
        labels.append(data[pos + 1 : pos + 1 + n].decode("utf-8", "replace"))
        pos += 1 + n
    return ".".join(labels), (end if end is not None else pos)


def build_mdns_query():
    header = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
    return header + _encode_name(MDNS_SERVICE) + struct.pack(">HH", 12, 1)  # PTR, IN


def parse_mdns_response(data):
    """Renvoie {'ptr': [...], 'srv': [(propriétaire, port, cible)]}."""
    _id, _flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    pos = 12
    for _ in range(qd):
        _, pos = _read_name(data, pos)
        pos += 4
    result = {"ptr": [], "srv": []}
    for _ in range(an + ns + ar):
        owner, pos = _read_name(data, pos)
        rtype, _rclass, _ttl, rdlen = struct.unpack(">HHIH", data[pos : pos + 10])
        rdata = pos + 10
        if rtype == 12:
            target, _ = _read_name(data, rdata)
            result["ptr"].append(target)
        elif rtype == 33:
            port = struct.unpack(">H", data[rdata + 4 : rdata + 6])[0]
            target, _ = _read_name(data, rdata + 6)
            result["srv"].append((owner, port, target))
        pos = rdata + rdlen
    return result


def _discover_dnspython(host, mdns_port, timeout, log):
    """Même principe que ew_api.py (V1) : dnspython, toutes les adresses de l'hôte comme serveurs."""
    import dns.exception
    import dns.message
    import dns.rdataclass
    import dns.rdatatype
    import dns.resolver

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [a[4][0] for a in socket.getaddrinfo(host, MDNS_PORT, proto=socket.IPPROTO_UDP)]
    resolver.port = mdns_port
    resolver.timeout = timeout
    log("  [dnspython] serveurs interrogés : %s (port %d)" % (resolver.nameservers, mdns_port))
    resolution = resolver.resolve(MDNS_SERVICE + ".", rdtype=dns.rdatatype.PTR)
    srv_name = resolution.rrset[0].target
    rrset = resolution.response.find_rrset(dns.message.ADDITIONAL, srv_name, dns.rdataclass.IN, dns.rdatatype.SRV)
    return rrset[0].port, {"ptr": [str(srv_name)], "methode": "dnspython"}


def _discover_manual(host, mdns_port, timeout, log, attempts=2):
    """Repli sans dépendance : requête mDNS unicast vers chaque adresse de l'hôte."""
    infos = socket.getaddrinfo(host, mdns_port, 0, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    seen, errors = set(), []
    for family, _, _, _, addr in infos:
        if addr in seen:
            continue
        seen.add(addr)
        for attempt in range(attempts):
            query_id = int.from_bytes(os.urandom(2), "big") or 1
            query = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)  # RD, comme dnspython
            query += _encode_name(MDNS_SERVICE) + struct.pack(">HH", 12, 1)
            log("  [manuel] requête PTR vers %s (essai %d)" % (addr[0], attempt + 1))
            try:
                with socket.socket(family, socket.SOCK_DGRAM) as s:
                    s.settimeout(timeout)
                    s.sendto(query, addr)
                    end = time.monotonic() + timeout
                    while time.monotonic() < end:
                        data, src = s.recvfrom(9000)
                        try:
                            parsed = parse_mdns_response(data)
                        except (ValueError, struct.error, IndexError):
                            continue
                        if not parsed["srv"]:
                            continue
                        parsed["methode"] = "manuel"
                        for owner, port, _target in parsed["srv"]:
                            if owner in parsed["ptr"]:
                                return port, parsed
                        return parsed["srv"][0][1], parsed
            except socket.timeout:
                errors.append("%s : pas de réponse en %.0f s" % (addr[0], timeout))
            except OSError as e:
                errors.append("%s : %s" % (addr[0], e))
                break
    raise RuntimeError("; ".join(errors) or "aucune réponse")


def discover_port(host, timeout=3.0, log=print, mdns_port=MDNS_PORT):
    """Trouve le port TCP de la télécommande. dnspython (comme la V1) si installé, sinon repli manuel."""
    try:
        import dns.resolver  # noqa: F401
    except ImportError:
        log("  dnspython absent : requête mDNS manuelle (pip install dnspython pour le comportement exact de la V1)")
    else:
        try:
            return _discover_dnspython(host, mdns_port, timeout, log)
        except Exception as e:  # noqa: BLE001 - on veut tout rapporter puis tenter le repli
            log("  [dnspython] échec : %s: %s" % (type(e).__name__, e))
    return _discover_manual(host, mdns_port, timeout, log)


###################################################################################################
##  Enregistrement                                                                               ##
###################################################################################################
class Recorder:
    def __init__(self, path, redact=False):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self.redact = redact
        self.t0 = time.monotonic()
        self._f = open(path, "w", encoding="utf-8", buffering=1)

    def close(self):
        self._f.close()

    def _mask(self, msg):
        if not self.redact or not isinstance(msg, dict):
            return msg
        return {
            k: ("<masqué len=%d>" % len(str(v)) if k in REDACT_KEYS else v) for k, v in msg.items()
        }

    def write(self, direction, msg=None, raw=None, extra=b"", **more):
        rec = {
            "t": round(time.monotonic() - self.t0, 3),
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "dir": direction,
        }
        if msg is not None:
            rec["msg"] = self._mask(msg)
        if raw is not None:
            rec["raw"] = raw
        if extra:
            rec["extra_len"] = len(extra)
            action = msg.get("action") if isinstance(msg, dict) else None
            if action in IMAGE_ACTIONS:  # images : taille + empreinte seulement
                rec["extra_sha1"] = hashlib.sha1(extra).hexdigest()
            else:
                rec["extra_b64"] = base64.b64encode(extra).decode("ascii")
        rec.update(more)
        self._f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec


###################################################################################################
##  Session de capture                                                                           ##
###################################################################################################
def decode_livedata(extra):
    """Décode le binaire de LiveData. Renvoie un dict (avec 'error' si incohérent)."""
    if len(extra) < LIVEDATA_HEADER.size:
        return {"error": "binaire trop court (%d octets)" % len(extra)}
    u0, liverev, pres_rowid, title_rev, pres_len, u5 = LIVEDATA_HEADER.unpack_from(extra)
    out = {
        "unknown0": u0,
        "liverev": liverev,
        "pres_rowid": pres_rowid,
        "title_revision": title_rev,
        "pres_len": pres_len,
        "unknown5": u5,
        "slides": [],
    }
    expected = LIVEDATA_HEADER.size + LIVEDATA_SLIDE.size * pres_len
    if pres_len < 0 or expected > len(extra):
        out["error"] = "pres_len=%d incompatible avec %d octets" % (pres_len, len(extra))
        return out
    for i in range(pres_len):
        rowid, rev = LIVEDATA_SLIDE.unpack_from(extra, LIVEDATA_HEADER.size + LIVEDATA_SLIDE.size * i)
        out["slides"].append({"rowid": rowid, "revision": rev})
    if expected != len(extra):
        out["warning"] = "%d octets non décodés après les diapos" % (len(extra) - expected)
    return out


class Session:
    def __init__(self, sock, recorder, active, client_id, log, device_name=V1_DEVICE_NAME):
        self.sock = sock
        self.rec = recorder
        self.active = active
        self.client_id = client_id
        self.device_name = device_name
        self.log = log
        self.buf = b""
        self.requestrev = 0
        self.liverev = None
        self.live_requested = None
        self.last_tx = 0.0

    # -- envoi ----------------------------------------------------------------------------------
    def send(self, msg):
        self.sock.sendall(json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\r\n")
        self.last_tx = time.monotonic()
        self.rec.write("send", msg=msg)
        self.log(">> " + self._summary(msg))

    def hello(self):
        self.send({"device_type": 0, "action": "connect", "uid": self.client_id, "device_name": self.device_name})

    def heartbeat_if_due(self):
        if time.monotonic() - self.last_tx > HEARTBEAT_EVERY:
            self.send({"action": "heartbeat", "requestrev": self.requestrev})

    # -- réception ------------------------------------------------------------------------------
    def feed(self, chunk):
        self.buf += chunk
        while True:
            end = self.buf.find(b"\r\n")
            if end == -1:
                return
            line = self.buf[:end]
            try:
                msg = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.rec.write("recv", raw=line.decode("utf-8", "replace"), error="json invalide")
                self.log("<< (JSON invalide) %r" % line[:80])
                self.buf = self.buf[end + 2 :]
                continue
            size = 0
            if isinstance(msg, dict) and msg.get("action") in EXTRA_ACTIONS:
                size = int(msg.get("size", 0))
            if len(self.buf) < end + 2 + size:
                return  # message incomplet : attendre la suite
            extra = self.buf[end + 2 : end + 2 + size]
            self.buf = self.buf[end + 2 + size :]
            self.handle(msg, extra)

    def handle(self, msg, extra):
        extras = {}
        action = msg.get("action") if isinstance(msg, dict) else None
        if action == "LiveData":
            extras["decoded"] = decode_livedata(extra)
        self.rec.write("recv", msg=msg, extra=extra, **extras)
        self.log("<< " + self._summary(msg, len(extra)))
        if "requestrev" in msg:
            try:
                self.requestrev = int(msg["requestrev"])
            except (TypeError, ValueError):
                pass
        if action == "notPaired":
            self.log("!! EN ATTENTE D'APPAIRAGE : acceptez la télécommande « %s » sur le PC EasyWorship." % self.device_name)
        if not self.active:
            return
        if action == "status" and "liverev" in msg:
            if msg["liverev"] != self.liverev and msg["liverev"] != self.live_requested:
                self.live_requested = msg["liverev"]
                self.send({"action": "GetLiveData", "requestrev": self.requestrev})
        elif action == "LiveData":
            d = extras["decoded"]
            if "error" in d:
                self.log("!! LiveData illisible : " + d["error"])
                return
            self.liverev = d["liverev"]
            self._get_slide_info(0, d["title_revision"], d["pres_rowid"])
            for s in d["slides"]:
                self._get_slide_info(s["rowid"], s["revision"], d["pres_rowid"])

    def _get_slide_info(self, rowid, revision, pres_rowid):
        self.send(
            {
                "slide_rowid": rowid,
                "revision": revision,
                "action": "getSlideInfo",
                "requestrev": self.requestrev,
                "rectype": 1,
                "pres_rowid": pres_rowid,
            }
        )

    @staticmethod
    def _summary(msg, extra_len=0):
        if not isinstance(msg, dict):
            return repr(msg)[:100]
        keys = ("action", "liverev", "imagehash", "slide_rowid", "logo", "black", "clear", "title")
        parts = ["%s=%s" % (k, str(msg[k])[:40]) for k in keys if k in msg]
        other = [k for k in msg if k not in keys]
        text = " ".join(parts)
        if other:
            text += " (+ %s)" % ",".join(other)
        if extra_len:
            text += " [+%d octets]" % extra_len
        return text


def capture(host, port, out, duration, active, redact, client_id, log=print, device_name=V1_DEVICE_NAME, mdns_port=MDNS_PORT):
    if port is None:
        log("Recherche du port EW par mDNS sur %s:%d ..." % (host, mdns_port))
        try:
            port, parsed = discover_port(host, log=log, mdns_port=mdns_port)
        except (OSError, RuntimeError, ValueError) as e:
            log("ECHEC de la découverte mDNS : %s" % e)
            log("Vérifiez que Bonjour est installé sur le PC EW et que la télécommande EW est activée,")
            log("ou donnez le port avec --port.")
            return None
        log("Port trouvé : %d  (%s)" % (port, parsed))
    log("Connexion à %s:%d ..." % (host, port))
    try:
        sock = socket.create_connection((host, port), 7)
    except OSError as e:
        log("ECHEC de la connexion : %s" % e)
        return None
    rec = Recorder(out, redact)
    rec.write("info", msg={"host": host, "port": port, "active": active, "redact": redact, "python": sys.version.split()[0]})
    session = Session(sock, rec, active, client_id, log, device_name)
    deadline = time.monotonic() + duration if duration else None
    log("Connecté. Capture dans %s (Ctrl+C pour arrêter)." % out)
    try:
        session.hello()
        sock.settimeout(0.2)
        while deadline is None or time.monotonic() < deadline:
            try:
                chunk = sock.recv(16384)
                if not chunk:
                    log("Connexion fermée par EW.")
                    rec.write("info", msg={"event": "closed_by_peer"})
                    break
                session.feed(chunk)
            except socket.timeout:
                pass
            session.heartbeat_if_due()
    except KeyboardInterrupt:
        log("Arrêt demandé.")
    except OSError as e:
        log("Erreur réseau : %s" % e)
        rec.write("info", msg={"event": "socket_error", "error": str(e)})
    finally:
        sock.close()
        rec.close()
    return out


###################################################################################################
##  Analyse                                                                                      ##
###################################################################################################
def load(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    print("ligne %d illisible dans %s" % (n, path))
    return recs


def analyze(path, out=print):
    recs = [r for r in load(path) if r.get("dir") in ("send", "recv")]
    stats = defaultdict(lambda: {"n": 0, "keys": Counter(), "extra": [], "first": None})
    warnings = []
    known_slides, seen_info = set(), set()
    status_vals = defaultdict(set)
    last_status_t = None
    latencies = []
    for r in recs:
        msg = r.get("msg")
        if msg is None:
            warnings.append("t=%s : ligne non JSON reçue : %r" % (r["t"], r.get("raw", "")[:60]))
            continue
        action = msg.get("action", "<sans action>")
        s = stats[(r["dir"], action)]
        s["n"] += 1
        s["keys"].update(msg.keys())
        if "extra_len" in r:
            s["extra"].append(r["extra_len"])
        if s["first"] is None:
            s["first"] = {k: (str(v)[:50]) for k, v in msg.items()}
        known = KNOWN_SENT if r["dir"] == "send" else KNOWN_RECV
        if action not in known:
            warnings.append("t=%s : action inconnue (%s) %s à documenter" % (r["t"], r["dir"], action))
        if r["dir"] == "recv" and "size" in msg and action not in EXTRA_ACTIONS:
            warnings.append("t=%s : '%s' a un champ size=%s mais n'est pas dans EXTRA_ACTIONS : cadrage à vérifier" % (r["t"], action, msg["size"]))
        if r["dir"] == "recv" and action in EXTRA_ACTIONS and r.get("extra_len", 0) != int(msg.get("size", 0)):
            warnings.append("t=%s : %s size=%s mais %s octets reçus" % (r["t"], action, msg.get("size"), r.get("extra_len", 0)))
        if action == "status":
            for k in ("liverev", "imagehash", "slide_rowid", "logo", "black", "clear"):
                if k in msg:
                    status_vals[k].add(str(msg[k]))
            last_status_t = r["t"]
        if action == "LiveData":
            d = r.get("decoded", {})
            for k in ("error", "warning"):
                if k in d:
                    warnings.append("t=%s : LiveData %s : %s" % (r["t"], k, d[k]))
            known_slides = {str(sl["rowid"]) for sl in d.get("slides", [])}
            if d.get("unknown0") not in (None, 1):  # toujours 1 dans la capture du 2026-10-23
                warnings.append("t=%s : header LiveData : unknown0=%s (valait 1 jusqu'ici)" % (r["t"], d.get("unknown0")))
        if action == "slideInfo":
            seen_info.add(msg.get("slide_rowid"))
            rid = str(msg.get("slide_rowid"))  # EW envoie les identifiants sous forme de chaînes
            if rid not in ("0", "None") and known_slides and rid not in known_slides:
                warnings.append("t=%s : slideInfo pour une diapo absente de LiveData (rowid=%s)" % (r["t"], rid))
            if last_status_t is not None:
                latencies.append(r["t"] - last_status_t)

    out("== %s : %d messages ==" % (path, len(recs)))
    out("")
    out("%-5s %-14s %6s  %s" % ("sens", "action", "nb", "champs (nb d'occurrences)"))
    for (d, a), s in sorted(stats.items()):
        keys = ", ".join("%s(%d)" % (k, c) if c != s["n"] else k for k, c in sorted(s["keys"].items()))
        out("%-5s %-14s %6d  %s" % (d, a, s["n"], keys))
        if s["extra"]:
            out("      octets joints : min=%d max=%d" % (min(s["extra"]), max(s["extra"])))
    out("")
    if status_vals:
        out("Valeurs distinctes dans 'status' :")
        for k, v in sorted(status_vals.items()):
            sample = sorted(v)[:6]
            out("  %-12s %d valeur(s) %s%s" % (k, len(v), sample, " ..." if len(v) > 6 else ""))
        out("")
    if latencies:
        out("Délai status -> slideInfo : médiane %.0f ms, max %.0f ms" % (1000 * sorted(latencies)[len(latencies) // 2], 1000 * max(latencies)))
        out("")
    out("Exemples (premier message de chaque type) :")
    for (d, a), s in sorted(stats.items()):
        out("  %s %s: %s" % (d, a, json.dumps(s["first"], ensure_ascii=False)))
    out("")
    if warnings:
        out("%d point(s) d'attention :" % len(warnings))
        for w in warnings[:50]:
            out("  - " + w)
    else:
        out("Aucun point d'attention.")
    return warnings


###################################################################################################
##  Autotest : faux EW local, aucun matériel nécessaire                                          ##
###################################################################################################
def _fake_ew(listener, done):
    """Rejoue un scénario minimal : status -> LiveData -> slideInfo -> changement de diapo -> noir."""
    conn, _ = listener.accept()
    conn.settimeout(5)
    buf = b""

    def tx(obj, extra=b""):
        if extra:
            obj = dict(obj, size=len(extra))
        conn.sendall(json.dumps(obj).encode() + b"\r\n" + extra)

    def status(h, rowid, black=False):
        tx({"action": "status", "requestrev": 1, "liverev": 7, "imagehash": h, "slide_rowid": rowid, "black": black})

    slides = [(11, 1), (12, 1)]
    infos_left = 3
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\r\n" in buf:
                line, buf = buf.split(b"\r\n", 1)
                msg = json.loads(line)
                a = msg.get("action")
                if a == "connect":
                    status("h1", 11)
                elif a == "GetLiveData":
                    body = LIVEDATA_HEADER.pack(0, 7, 99, 3, len(slides), 0)
                    body += b"".join(LIVEDATA_SLIDE.pack(*s) for s in slides)
                    tx({"action": "LiveData", "requestrev": 1}, body)
                elif a == "getSlideInfo":
                    rid = msg["slide_rowid"]
                    tx({"action": "slideInfo", "slide_rowid": rid, "title": "Titre %d" % rid, "content": "Ligne A\nLigne B (%d)" % rid})
                    infos_left -= 1
                    if infos_left == 0:
                        time.sleep(0.2)
                        status("h2", 12)
                        time.sleep(0.2)
                        status("h2", 12, black=True)
                        time.sleep(0.2)
                        tx({"action": "inconnue_test", "x": 1})
                        time.sleep(0.2)
                        return
    except (OSError, socket.timeout):
        pass
    finally:
        done.set()
        conn.close()


def _fake_mdns_response(query, tcp_port):
    """Réponse mDNS « legacy unicast » : écho de l'id et de la question, PTR + SRV (noms compressés)."""
    pkt = query[:2] + struct.pack(">HHHHH", 0x8400, 1, 1, 0, 1) + query[12:]
    inst = bytes([8]) + b"PC-REGIE" + b"\xc0\x0c"  # pointeur vers le nom du service (offset 12)
    pkt += b"\xc0\x0c" + struct.pack(">HHIH", 12, 1, 120, len(inst))
    inst_off = len(pkt)
    pkt += inst
    srv = struct.pack(">HHH", 0, 0, tcp_port) + _encode_name("PC-REGIE.local")
    pkt += struct.pack(">H", 0xC000 | inst_off) + struct.pack(">HHIH", 33, 1, 120, len(srv)) + srv
    return pkt


def _fake_mdns_server(udp, tcp_port):
    udp.settimeout(5)
    try:
        while True:
            data, src = udp.recvfrom(2048)
            udp.sendto(_fake_mdns_response(data, tcp_port), src)
    except (OSError, socket.timeout):
        pass


def selftest():
    ok = True

    def check(cond, label):
        nonlocal ok
        print("  [%s] %s" % ("ok" if cond else "ECHEC", label))
        ok = ok and cond

    print("Test 1 : réponse mDNS (noms compressés) décodée par le parseur manuel")
    query = struct.pack(">HHHHHH", 4242, 0x0100, 1, 0, 0, 0) + _encode_name(MDNS_SERVICE) + struct.pack(">HH", 12, 1)
    parsed = parse_mdns_response(_fake_mdns_response(query, 51234))
    check(parsed["ptr"] == ["PC-REGIE._ezwremote._tcp.local"], "PTR décodé : %s" % parsed["ptr"])
    check(parsed["srv"] == [("PC-REGIE._ezwremote._tcp.local", 51234, "PC-REGIE.local")], "SRV décodé : %s" % parsed["srv"])

    print("Test 2 : découverte du port contre un faux répondeur mDNS (UDP local)")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp_port = udp.getsockname()[1]
    threading.Thread(target=_fake_mdns_server, args=(udp, port), daemon=True).start()
    quiet = lambda *_: None
    found, _ = _discover_manual("127.0.0.1", udp_port, 2, quiet)
    check(found == port, "découverte manuelle : port %d" % found)
    try:
        import dns.resolver  # noqa: F401
    except ImportError:
        print("  [--] dnspython absent : chemin dnspython non testé")
    else:
        found, _ = _discover_dnspython("127.0.0.1", udp_port, 2, quiet)
        check(found == port, "découverte dnspython : port %d" % found)

    print("Test 3 : capture complète contre un faux EW (port trouvé par mDNS, identité V1)")
    done = threading.Event()
    threading.Thread(target=_fake_ew, args=(listener, done), daemon=True).start()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures", "selftest.jsonl")
    path = os.path.normpath(path)
    logs = []
    res = capture("127.0.0.1", None, path, 10, True, False, V1_CLIENT_ID, log=logs.append, mdns_port=udp_port)
    done.wait(2)
    listener.close()
    udp.close()
    check(res == path, "fichier de capture produit")
    recs = [r for r in load(path) if r.get("dir") in ("send", "recv")]
    acts = Counter((r["dir"], r["msg"].get("action")) for r in recs if "msg" in r)
    hello = next(r for r in recs if r["msg"].get("action") == "connect")
    check(hello["msg"]["uid"] == V1_CLIENT_ID and hello["msg"]["device_name"] == V1_DEVICE_NAME, "connect avec l'uid et le nom de la V1")
    check(acts[("recv", "LiveData")] == 1, "LiveData reçu")
    check(acts[("send", "getSlideInfo")] == 3, "3 getSlideInfo envoyés (titre + 2 diapos)")
    check(acts[("recv", "slideInfo")] == 3, "3 slideInfo reçus")
    check(acts[("recv", "status")] == 3, "3 status reçus")
    live = next(r for r in recs if r["msg"].get("action") == "LiveData")
    check(live["decoded"]["pres_len"] == 2 and len(live["decoded"]["slides"]) == 2, "binaire LiveData décodé")

    print("Test 4 : analyse du fichier")
    lines = []
    warns = analyze(path, out=lines.append)
    check(any("inconnue_test" in w for w in warns), "action inconnue signalée")
    check(any("Valeurs distinctes" in l for l in lines), "résumé des valeurs de status")
    print("\n".join("    " + l for l in lines))
    print("\nAUTOTEST " + ("RÉUSSI" if ok else "ÉCHOUÉ"))
    return 0 if ok else 1


###################################################################################################
##  CLI                                                                                          ##
###################################################################################################
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="Capture et analyse des trames de la télécommande EasyWorship.")
    p.add_argument("host", nargs="?", help="nom ou IP du PC EasyWorship")
    p.add_argument("--port", type=int, help="port TCP de la télécommande (sinon découvert par mDNS)")
    p.add_argument("--duration", type=float, default=60, help="durée en secondes (0 = jusqu'à Ctrl+C), défaut 60")
    p.add_argument("--out", help="fichier de sortie (défaut captures/ew_capture_DATE.jsonl)")
    p.add_argument("--passive", action="store_true", help="n'envoie que connect et heartbeat")
    p.add_argument("--redact", action="store_true", help="masque titres et contenus dans le fichier")
    p.add_argument("--client-id", default=V1_CLIENT_ID, help="uid de télécommande (défaut : celui de la V1)")
    p.add_argument("--device-name", default=V1_DEVICE_NAME, help="nom de télécommande (défaut : celui de la V1)")
    p.add_argument("--no-analyze", action="store_true", help="ne pas analyser à la fin")
    p.add_argument("--analyze", metavar="FICHIER", help="analyser un fichier de capture existant")
    p.add_argument("--selftest", action="store_true", help="tester le script avec un faux EW local")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.analyze:
        analyze(args.analyze)
        return 0
    if not args.host:
        p.error("indiquez le PC EasyWorship (ou --analyze / --selftest)")
    out = args.out or os.path.join("captures", "ew_capture_%s.jsonl" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    path = capture(args.host, args.port, out, args.duration, not args.passive, args.redact, args.client_id, device_name=args.device_name)
    if path is None:
        return 2
    if not args.no_analyze:
        print("")
        analyze(path)
    print("\nCapture enregistrée : %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
