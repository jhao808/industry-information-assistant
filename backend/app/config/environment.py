"""Load a fixed backend/.env without logging credentials.

Local default: file wins. Deployments may set APP_CONFIG_SOURCE=environment.
"""
import logging
import os
from pathlib import Path
from dotenv import dotenv_values

ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
_loaded = False

def load_environment():
    global _loaded
    if _loaded:
        return
    mode = os.environ.get('APP_CONFIG_SOURCE', 'file')
    if mode not in {'file', 'environment'}:
        raise ValueError('APP_CONFIG_SOURCE must be file or environment')
    values = dotenv_values(ENV_PATH, interpolate=False) if ENV_PATH.exists() else {}
    logger = logging.getLogger(__name__)
    for name, value in values.items():
        if value is not None and (mode == 'file' or name not in os.environ):
            if name in os.environ and os.environ[name] != value:
                logger.warning('%s: backend/.env overrides inherited environment (value hidden)', name)
            os.environ[name] = value
    for name in ('DASHSCOPE_API_KEY', 'BOCHA_API_KEY'):
        value = os.environ.get(name, '').strip()
        while value.lower().startswith('bearer '):
            value = value[7:].strip()
        os.environ[name] = value
        source = 'backend/.env' if name in values and mode == 'file' else 'environment/fallback'
        logger.info('%s: source=%s, configured=%s', name, source, bool(value))
    # Keep older modules on the same model endpoint.
    if os.environ.get('LLM_BASE_URL'):
        for name in ('DASHSCOPE_BASE_URL', 'OPENAI_BASE_URL'):
            os.environ[name] = os.environ['LLM_BASE_URL']
    if os.environ.get('LLM_MAIN_MODEL'):
        os.environ['OPENAI_MODEL'] = os.environ['LLM_MAIN_MODEL']
    if os.environ.get('LLM_FAST_MODEL'):
        os.environ['DASHSCOPE_MODEL'] = os.environ['LLM_FAST_MODEL']
    _loaded = True
