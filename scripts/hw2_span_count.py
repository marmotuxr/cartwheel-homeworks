"""Regenerate a trace's span count from Langfuse, without a model call."""
from __future__ import annotations

import argparse
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

import httpx

REPO_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO_ROOT))


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace_id')
    parser.add_argument('--local',action='store_true',help='Use the course local instance')
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}',args.trace_id):
        parser.error('Use a 32-character trace ID copied from Langfuse')
    if args.local:
        from hw2_local import configure_local_tracing
        configure_local_tracing()
    else:
        from observability.instrument import load_env
        load_env()
    host=os.environ.get('LANGFUSE_BASE_URL') or os.environ.get('LANGFUSE_HOST','')
    cloud=(urlparse(host).hostname or '').endswith('cloud.langfuse.com')
    try:
        with httpx.Client(base_url=host,auth=(os.environ['LANGFUSE_PUBLIC_KEY'],os.environ['LANGFUSE_SECRET_KEY']),timeout=30) as api:
            if cloud:
                now=datetime.now(timezone.utc)
                params={'traceId':args.trace_id,'fields':'core,basic','limit':100,'fromStartTime':(now-timedelta(days=7)).isoformat(),'toStartTime':(now+timedelta(minutes=1)).isoformat()}
                rows=[]
                while True:
                    response=api.get('/api/public/v2/observations',params=params)
                    response.raise_for_status()
                    page=response.json()
                    rows.extend(page['data'])
                    cursor=page.get('meta',{}).get('cursor')
                    if not cursor:break
                    params['cursor']=cursor
            else:
                response=api.get('/api/public/traces/'+args.trace_id)
                response.raise_for_status()
                rows=response.json().get('observations',[])
        unique={row['id']:row for row in rows}
        if not unique:raise ValueError('No recorded spans were returned')
        print('Trace:',args.trace_id)
        print('Span count:',len(unique))
        for row in sorted(unique.values(),key=lambda x:x.get('startTime','')):
            print(' -',row.get('name','unnamed'))
    except (httpx.HTTPError,KeyError,ValueError) as exc:
        print('Could not count spans. Check that Langfuse is running and the trace ID is correct. ('+type(exc).__name__+')',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':
    main()
