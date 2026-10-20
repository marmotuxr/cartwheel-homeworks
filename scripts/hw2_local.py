"""Run the course's local Langfuse target without editing the user's .env."""
from __future__ import annotations

import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def configure_local_tracing() -> None:
    from observability.instrument import load_env

    load_env()  # retain the user's model provider configuration
    for line in (REPO_ROOT / '.env.example').read_text().splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        key,value=line.split('=',1)
        if key.strip() in {'LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','LANGFUSE_HOST'}:
            os.environ[key.strip()]=value.strip()
    os.environ['LANGFUSE_BASE_URL']=os.environ['LANGFUSE_HOST']
    os.environ['TRACELOOP_TRACE_CONTENT']='true'


if __name__ == '__main__':
    configure_local_tracing()
    import uvicorn
    from server.app import app

    print('Local Cartwheel chat: http://127.0.0.1:8012/')
    print('Local Langfuse: http://localhost:3000/')
    uvicorn.run(app, host='127.0.0.1', port=8012)
