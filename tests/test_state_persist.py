import os
import importlib.util

# load module from path
mod_path = os.path.join(os.path.dirname(__file__), '..', 'XNOR LOMOMELEDOR.py')
spec = importlib.util.spec_from_file_location('xnor_mod', mod_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_xnor_toggle_persistence(tmp_path, monkeypatch):
    # configure a temporary state file
    state_file = tmp_path / 'state.json.enc'
    monkeypatch.setattr(mod, 'STATE_FILE', str(state_file))
    # start with fresh state
    if os.path.exists(str(state_file)):
        os.remove(str(state_file))
    st = mod.load_state()
    assert 'use_xnor' in st
    assert st['use_xnor'] is False
    # toggle and save
    st['use_xnor'] = True
    mod.STATE = st
    mod.save_state()
    # load again
    st2 = mod.load_state()
    assert st2['use_xnor'] is True