import importlib.util

spec = importlib.util.spec_from_file_location('xnor', 'XNOR LOMOMELEDOR.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_create_onion_no_control_port():
    # Simulate stem being available but Tor control port not listening
    mod.STEM_OK = True
    logs = []
    mod.create_onion(lambda m: logs.append(m))
    assert any('control port not available' in s.lower() for s in logs), "Expected friendly control-port message"
