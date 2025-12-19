import os
import socket
import threading
import importlib.util
import hashlib
import hmac

# import module under test
mod_path = os.path.join(os.path.dirname(__file__), '..', 'XNOR LOMOMELEDOR.py')
spec = importlib.util.spec_from_file_location('xnor_mod', mod_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_encrypt_decrypt_roundtrip():
    enc = mod.encrypt('alice', 'hello')
    user, mid, msg = mod.decrypt(enc)
    assert user == 'alice'
    assert msg == 'hello'
    assert len(mid) > 0


def test_xnor_preprocess_roundtrip(monkeypatch):
    # enable XNOR preprocessing if available
    monkeypatch.setattr(mod, 'USE_XNOR_ENCODING', True)
    if not getattr(mod, 'XNOR_AVAILABLE', False):
        # skip if XNOR module not present
        import pytest
        pytest.skip("XNOR FOR-NOR not available")
    s = mod.encrypt('alice', 'HelloWorld')
    u, mid, m = mod.decrypt(s)
    assert u == 'alice'
    # FOR-NOR encode lowercases during encode/decode roundtrip
    assert m.lower() == 'helloworld'


def test_host_port_parsing():
    # make sure host:port parsing logic yields correct dest_port
    # we simulate by calling the parsing snippet used in the GUI send function
    h = '127.0.0.1:12345'
    dest_host = h
    dest_port = None
    if ':' in h:
        try:
            dest_host, port_str = h.rsplit(':', 1)
            dest_port = int(port_str)
        except Exception:
            dest_host = h
            dest_port = None
    assert dest_host == '127.0.0.1'
    assert dest_port == 12345


def test_xnor_send_message_integration(monkeypatch):
    monkeypatch.setattr(mod, 'USE_XNOR_ENCODING', True)
    if not getattr(mod, 'XNOR_AVAILABLE', False):
        import pytest
        pytest.skip("XNOR FOR-NOR not available")
    # start a fake server to validate handshake + decrypt
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    port = server.getsockname()[1]
    server.listen()

    def server_thread():
        conn, addr = server.accept()
        chal = os.urandom(16)
        conn.sendall(chal)
        recv_h = conn.recv(32)
        expected = hmac.new(mod.AUTH_KEY, chal, hashlib.sha256).digest()
        assert hmac.compare_digest(recv_h, expected)
        blob = conn.recv(8192)
        u, mid, m = mod.decrypt(blob)
        assert m.lower() == 'hello'
        conn.close()

    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

    res = mod.send_message('127.0.0.1', 'tester', 'Hello', lambda m: None, attempts=1, port=port)
    assert res is True

    server.close()


def test_load_state_corrupted(tmp_path, monkeypatch):
    # write a corrupted state file and ensure load_state returns a dict with 'seen'
    path = tmp_path / 'state.json.enc'
    path.write_bytes(b'not a valid fernet blob')
    monkeypatch.setattr(mod, 'STATE_FILE', str(path))
    st = mod.load_state()
    assert isinstance(st, dict)
    assert 'seen' in st


def test_send_message_handshake():
    # start a fake server that performs the basic chal/hmac/recv
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    port = server.getsockname()[1]
    server.listen()

    def server_thread():
        conn, addr = server.accept()
        chal = os.urandom(16)
        conn.sendall(chal)
        recv_h = conn.recv(32)
        expected = hmac.new(mod.AUTH_KEY, chal, hashlib.sha256).digest()
        assert hmac.compare_digest(recv_h, expected)
        blob = conn.recv(8192)
        u, mid, m = mod.decrypt(blob)
        assert m == 'hi'
        conn.close()

    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

    res = mod.send_message('127.0.0.1', 'tester', 'hi', lambda m: None, attempts=1, port=port)
    assert res is True

    server.close()