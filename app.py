import importlib.util
import os

_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code sa cpe laws.py")
_spec = importlib.util.spec_from_file_location("karinderya_main", _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
_module.init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
