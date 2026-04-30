import builtins
import json
from pathlib import Path

base = Path(r'd:/新建文件夹/long_term_dca_portfolio_assistant')

def fetch(url, *args, **kwargs):
    class Resp:
        def __init__(self, path):
            self.path = path
            self.ok = path.exists()
            self.status = 200 if self.ok else 404
        def json(self):
            return json.loads(self.path.read_text(encoding='utf-8'))
        def text(self):
            return self.path.read_text(encoding='utf-8')
    prefix = '/archive-data/'
    if not url.startswith(prefix):
        raise RuntimeError(url)
    rel = url[len(prefix):]
    return Resp(base / rel)

builtins.fetch = fetch
