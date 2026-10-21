"""Harness exclusivo de testes; não é entrada de produção nem usa a API real."""

import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aplicacao.gemini_client import GeminiClient, GeminiError
from testes.test_analyzer import result_json
from testes.test_explanation import explanation
from testes.test_requisitos import sample_payload


def fake_analyze(self, prompt, schema=None):
    if 'FALHA_GEMINI' in prompt:
        raise GeminiError('Serviço Gemini simulado indisponível. Tente novamente.')
    properties = (schema or {}).get('properties', {})
    if 'requirements' in properties:
        return json.dumps(sample_payload(), ensure_ascii=False)
    if 'execution_flow' in properties:
        return explanation('FUNCTION cad0001_main()')
    return result_json('LET l_val_calculado = (p_val1 * p_val2) + p_val3')


# Dedicated test process: keep the replacement stable across Streamlit reruns.
# A restoring context manager can race with a rerun interrupted by a new upload.
GeminiClient.analyze = fake_analyze
runpy.run_path(str(ROOT/'app.py'),run_name='__main__')

import streamlit as st
st.caption('Ambiente de validação: respostas Gemini simuladas, sem consumo da API.')
