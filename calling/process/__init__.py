"""Process backend selection.

Phase 1 ships a Windows ReadProcessMemory backend.
"""
import platform

_system = platform.system()

if _system == "Windows":
    from . import windows as backend
    Backend = backend.Backend
    find_pid = backend.find_pid
    CallError = backend.CallError
    Injector = backend.Injector
else:
    # Importable on Linux build agents; attach still requires Windows.
    CallError = RuntimeError

    def find_pid(name="hoi4.exe"):
        return None

    class Backend:
        def __init__(self, *a, **k):
            raise RuntimeError("Windows Backend requires Windows to attach to hoi4.exe")

    class Injector:
        def __init__(self, *a, **k):
            raise CallError("Injector requires Windows Phase 2")
