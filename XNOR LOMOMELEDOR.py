import os
import time
import json
import socket
import hashlib
import hmac
import threading
import base64
import socks
import tkinter as tk
from tkinter import scrolledtext, messagebox
from cryptography.fernet import Fernet
import logging
import logging.handlers
import codecs

try:
    from stem.control import Controller  # type: ignore[reportMissingImports]
    STEM_OK = True
except Exception:
    STEM_OK = False
    # stem not available: keep going without TOR control

PORT = 9000
TOR_PROXY = ("127.0.0.1", 9050)

SEED = "XNOR__-//-__?++?_--_--_/||/_AaaA_TttT_--__-__-__---__---_-__-_-_--__-_-__-___-_-_-___-_--__-__---_____----_-_-_-_---_-_-_??++||++=000000"
AUTH_KEY = b"CLIENT_SHARED_SECRET"

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "state.json.enc")

USE_TOR = False
SERVER_RUNNING = False
STATE_LOCK = threading.Lock()
SOCKET_TIMEOUT = 5.0  # seconds for outgoing sockets
HEARTBEAT_INTERVAL = 5.0  # seconds between heartbeats
LAST_HEARTBEAT = None

# logging setup
def setup_logging():
    logs_dir = os.path.join(BASE, "logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        pass
    logger = logging.getLogger("xnor")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.handlers.RotatingFileHandler(os.path.join(logs_dir, "xnor.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(ch)
    return logger

LOGGER = setup_logging()

# Optional integration with local encoder script `XNOR FOR-NOR.py`
USE_XNOR_ENCODING = False

def _load_xnor_safe():
    # Safely load only the encode/decode/make_cipher constants from the script
    path = os.path.join(BASE, "XNOR FOR-NOR.py")
    if not os.path.exists(path):
        return None, False
    import ast
    try:
        src = open(path, "r", encoding="utf-8").read()
        mod_ast = ast.parse(src, path)
        allowed_names = {"ALPHABET", "SEED", "KEY", "PROKey", "make_cipher", "encode", "decode"}
        new_nodes = []
        for node in mod_ast.body:
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if any(t in allowed_names for t in targets):
                    new_nodes.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name in allowed_names:
                new_nodes.append(node)
        new_mod = ast.Module(body=new_nodes, type_ignores=[])
        compiled = compile(ast.fix_missing_locations(new_mod), path, "exec")
        ns = {}
        exec(compiled, ns)
        class SimpleMod:
            pass
        sm = SimpleMod()
        sm.encode = ns.get("encode")
        sm.decode = ns.get("decode")
        sm.SEED = ns.get("SEED")
        return sm, True
    except Exception:
        LOGGER.exception("failed to load XNOR module safely")
        return None, False

xnor_mod, XNOR_AVAILABLE = _load_xnor_safe()
if XNOR_AVAILABLE:
    LOGGER.info("XNOR FOR-NOR available (safe loader)")
else:
    LOGGER.info("XNOR FOR-NOR not available or failed to load safely")

def master_key():
    return hashlib.sha256(SEED.encode()).digest()

def fernet():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(master_key()).digest()))

def hmac_key():
    return hashlib.sha256(master_key() + b"H").digest()

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen": [], "use_xnor": False}
    try:
        with open(STATE_FILE, "rb") as f:
            data = f.read()
        st = json.loads(fernet().decrypt(data).decode())
        # ensure required keys
        if "seen" not in st:
            st["seen"] = []
        if "use_xnor" not in st:
            st["use_xnor"] = False
        return st
    except Exception:
        # failed to read or decrypt state; start fresh and log the error
        LOGGER.exception("load_state error")
        return {"seen": [], "use_xnor": False}

STATE = load_state()
# initialize runtime XNOR setting from state so GUI toggle persists
USE_XNOR_ENCODING = STATE.get("use_xnor", USE_XNOR_ENCODING)

def save_state():
    with STATE_LOCK:
        try:
            with open(STATE_FILE, "wb") as f:
                f.write(fernet().encrypt(json.dumps(STATE).encode()))
        except Exception:
            # best-effort save; report failure
            LOGGER.exception("save_state error")

def keystream(nonce, n):
    out = b""
    i = 0
    while len(out) < n:
        out += hashlib.sha256(master_key() + nonce + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]

def encrypt(user,msg):
    # Optional pre-encode with XNOR FOR-NOR
    msg_to_use = msg
    if USE_XNOR_ENCODING and XNOR_AVAILABLE:
        try:
            msg_to_use = xnor_mod.encode(msg, SEED)
        except Exception:
            LOGGER.exception("XNOR encode failed; falling back to raw message")
            msg_to_use = msg
    # encode the message robustly: plaintext bytes XORed with keystream, then base64-encoded
    # then encrypt with Fernet, base64 the token, and apply ROT13 to the base64 string
    nonce = os.urandom(8)
    mid = os.urandom(6).hex()
    text = (user+"|"+mid+"|"+msg_to_use).encode("utf-8")
    ks = keystream(nonce, len(text))
    xored = bytes([b ^ k for b,k in zip(text, ks)])
    b64 = base64.urlsafe_b64encode(xored)
    payload = nonce + b64
    mac = hmac.new(hmac_key(), payload, hashlib.sha256).digest()
    token = fernet().encrypt(mac + payload)
    # token -> base64 string -> rot13 -> bytes
    token_b64 = base64.urlsafe_b64encode(token).decode('ascii')
    token_rot = codecs.encode(token_b64, 'rot_13')
    return token_rot.encode('ascii')

def decrypt(blob):
    # inverse of encrypt: ROT13 -> base64 -> Fernet decrypt -> verify HMAC -> recover plaintext
    try:
        token_rot = blob.decode('ascii')
        token_b64 = codecs.encode(token_rot, 'rot_13')
        token = base64.urlsafe_b64decode(token_b64)
    except Exception:
        LOGGER.exception("decrypt: invalid token encoding")
        raise
    data = fernet().decrypt(token)
    mac, payload = data[:32], data[32:]
    if not hmac.compare_digest(mac, hmac.new(hmac_key(), payload, hashlib.sha256).digest()):
        raise ValueError("mac mismatch")
    nonce = payload[:8]
    b64 = payload[8:]
    xored = base64.urlsafe_b64decode(b64)
    ks = keystream(nonce, len(xored))
    txt = bytes([c ^ k for c,k in zip(xored, ks)])
    user, mid, msg = txt.decode("utf-8").split("|",2)
    if USE_XNOR_ENCODING and XNOR_AVAILABLE:
        try:
            msg = xnor_mod.decode(msg, SEED)
        except Exception:
            LOGGER.exception("XNOR decode failed; returning raw message")
    return user, mid, msg

def make_socket():
    # create a socket and set a sensible timeout to avoid blocking forever
    if USE_TOR:
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, *TOR_PROXY)
        try:
            s.settimeout(SOCKET_TIMEOUT)
        except Exception:
            pass
        return s
    s = socket.socket()
    try:
        s.settimeout(SOCKET_TIMEOUT)
    except Exception:
        pass
    return s

def tor_status():
    s = None
    try:
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5,*TOR_PROXY)
        s.settimeout(3.0)
        s.connect(("check.torproject.org",80))
        return True
    except Exception:
        # TOR not reachable or proxy not running
        # print("tor_status: <error>")
        return False
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass

def handle_client(c,a,log):
    try:
        chal=os.urandom(16)
        c.sendall(chal)
        if not hmac.compare_digest(c.recv(32),hmac.new(AUTH_KEY,chal,hashlib.sha256).digest()):
            return
        user,mid,msg=decrypt(c.recv(8192))
        if mid in STATE["seen"]:
            return
        STATE["seen"].append(mid)
        STATE["seen"]=STATE["seen"][-500:]
        save_state()
        log(user+": "+msg)
    except Exception as e:
        # surface errors to the GUI log for easier debugging
        try:
            log("handle_client error: "+str(e))
        except Exception:
            LOGGER.exception("handle_client error")
    finally:
        c.close() 

def server_thread(log):
    global SERVER_RUNNING
    try:
        s=make_socket()
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind(("0.0.0.0",PORT))
        s.listen()
        SERVER_RUNNING=True
        log("listening")
        while True:
            c,a=s.accept()
            threading.Thread(target=handle_client,args=(c,a,log),daemon=True).start()
    except Exception as e:
        SERVER_RUNNING=False
        try:
            log("server stopped: "+str(e))
        except Exception:
            LOGGER.exception("server stopped") 

def send_message(host,user,msg,log, attempts=3, backoff=0.5, port=None):
    """Send a message with retries and timeouts. Non-blocking callers should run this in a thread.

    Optional `port` overrides the module-level PORT to allow tests or alternative ports.
    """
    last_exc = None
    dest_port = PORT if port is None else port
    for attempt in range(1, attempts+1):
        s = None
        try:
            s = make_socket()
            LOGGER.info("connect attempt %d to %s:%d", attempt, host, dest_port)
            s.connect((host, dest_port))
            chal = s.recv(16)
            s.sendall(hmac.new(AUTH_KEY, chal, hashlib.sha256).digest())
            s.sendall(encrypt(user, msg))
            log("you: " + msg)
            try:
                s.close()
            except Exception:
                pass
            return True
        except Exception as e:
            last_exc = e
            LOGGER.warning("send attempt %d failed: %s", attempt, e)
            try:
                if s:
                    s.close()
            except Exception:
                pass
            if attempt < attempts:
                time.sleep(backoff * attempt)
            continue
    # All attempts failed
    try:
        log("send failed: %s" % str(last_exc))
    except Exception:
        LOGGER.exception("send failed and cannot log to UI")
    try:
        messagebox.showwarning("Network", "Cannot connect after %d attempts: %s" % (attempts, str(last_exc)))
    except Exception:
        LOGGER.exception("messagebox.showwarning failed")
    return False

def create_onion(log, control_host="127.0.0.1", control_port=9051):
    if not STEM_OK:
        # Avoid calling GUI messagebox from worker thread; log instead
        log("TOR: stem not installed")
        return
    # Probe the control port quickly so we can give a friendly message when Tor isn't running
    try:
        probe = socket.create_connection((control_host, control_port), timeout=1)
        probe.close()
    except Exception as e:
        log(f"TOR control port not available on {control_host}:{control_port}: {e}. Is Tor running and is ControlPort enabled?")
        LOGGER.warning("Tor control port not available at %s:%s: %s", control_host, control_port, e)
        return
    try:
        with Controller.from_port(address=control_host, port=control_port) as c:
            c.authenticate()
            res = c.create_ephemeral_hidden_service({PORT: PORT}, await_publication=True)
            log("XNOR service: " + res.service_id + ".onion")
    except Exception as e:
        # For connection-related errors, log a warning (no traceback). For other errors, keep the exception log.
        msg = str(e)
        if isinstance(e, ConnectionRefusedError) or e.__class__.__name__ == "SocketError":
            log(f"Failed to create onion (control port issue): {msg}")
            LOGGER.warning("create_onion failed (control port): %s", msg)
        else:
            log(f"Failed to create onion: {msg}")
            LOGGER.exception("create_onion failed") 

def gui():
    import traceback
    LOGGER.info("GUI: starting")
    root=tk.Tk()
    root.title("XNOR CHAT")

    out=scrolledtext.ScrolledText(root, width=70, height=20)
    out.pack()

    # catch uncaught exceptions from tkinter callbacks and show them in the UI and console
    def _report_callback(exc, val, tb):
        msg = ''.join(traceback.format_exception(exc, val, tb))
        try:
            out.insert(tk.END, time.strftime("%H:%M:%S ")+"Uncaught exception:\n"+msg+"\n")
            out.see(tk.END)
        except Exception:
            LOGGER.exception("Uncaught exception while reporting callback")
        LOGGER.exception("Uncaught exception in tkinter callback:\n%s", msg)
    root.report_callback_exception = _report_callback

    bar = tk.Frame(root)
    bar.pack()
    entry = tk.Entry(bar, width=40)
    entry.pack(side=tk.LEFT)
    host = tk.Entry(bar, width=25)
    host.insert(0, "127.0.0.1")
    host.pack(side=tk.LEFT)
    user = tk.Entry(bar, width=10)
    user.insert(0, "user")
    user.pack(side=tk.LEFT)

    status=tk.StringVar()
    status.set("TOR: OFF")
    tk.Label(root,textvariable=status).pack()

    # XNOR preprocessing toggle
    xnor_var = tk.BooleanVar(value=USE_XNOR_ENCODING)
    def _toggle_xnor():
        global USE_XNOR_ENCODING
        USE_XNOR_ENCODING = bool(xnor_var.get())
        # persist preference in state
        STATE["use_xnor"] = bool(USE_XNOR_ENCODING)
        try:
            save_state()
        except Exception:
            LOGGER.exception("failed to save state after toggling XNOR")
        log("XNOR preprocessing: %s" % ("ON" if USE_XNOR_ENCODING else "OFF"))
    xnor_cb = tk.Checkbutton(root, text="Use XNOR preprocessing", variable=xnor_var, command=_toggle_xnor)
    xnor_cb.pack()

    def log(m):
        # log to both the GUI output area and the file/console logger
        out.insert(tk.END,time.strftime("%H:%M:%S ")+m+"\n")
        out.see(tk.END)
        try:
            LOGGER.info(m)
        except Exception:
            pass

    def toggle_tor():
        global USE_TOR
        USE_TOR = not USE_TOR
        # do quick UI update then check TOR in background (may block network)
        status.set("TOR: Checking..." if USE_TOR else "TOR: OFF")
        def _check():
            connected = tor_status() if USE_TOR else False
            new = "TOR: CONNECTED" if USE_TOR and connected else "TOR: OFF"
            root.after(0, lambda: status.set(new))
        threading.Thread(target=_check, daemon=True).start()
        # also log the toggle action
        LOGGER.info("TOR toggled to %s", USE_TOR)

    def send():
        if entry.get():
            msg = entry.get()
            entry.delete(0,tk.END)
            # parse host:port if provided
            host_entry = host.get().strip()
            dest_host = host_entry
            dest_port = None
            if ":" in host_entry:
                try:
                    dest_host, port_str = host_entry.rsplit(":", 1)
                    dest_port = int(port_str)
                except Exception:
                    log("Invalid host:port, using host and default port")
                    dest_host = host_entry
                    dest_port = None
            # perform network send in background to avoid blocking the GUI
            threading.Thread(target=send_message, args=(dest_host, user.get(), msg, log), kwargs={"port": dest_port}, daemon=True).start()
            LOGGER.info("Queued message for send to %s", host_entry)

    threading.Thread(target=server_thread,args=(log,),daemon=True).start()

    # start a heartbeat thread to update UI and logs periodically
    def _heartbeat():
        global LAST_HEARTBEAT
        while True:
            LAST_HEARTBEAT = time.time()
            ts = time.strftime("%H:%M:%S ")
            try:
                root.after(0, lambda: log("heartbeat: %s" % ts))
            except Exception:
                LOGGER.info("heartbeat: %s", ts)
            time.sleep(HEARTBEAT_INTERVAL)
    threading.Thread(target=_heartbeat, daemon=True).start()

    tk.Button(bar,text="Send",command=send).pack(side=tk.LEFT)
    tk.Button(bar,text="Toggle TOR",command=toggle_tor).pack(side=tk.LEFT)
    tk.Button(bar,text="Create XNOR Onion",command=lambda: threading.Thread(target=create_onion, args=(log,), daemon=True).start()).pack(side=tk.LEFT)

    LOGGER.info("GUI: entering mainloop")
    root.mainloop()
    LOGGER.info("GUI: mainloop exited")

if __name__ == "__main__":
    try:
        gui()
    except Exception:
        LOGGER.exception("GUI failed on startup")
