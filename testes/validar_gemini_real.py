"""Smoke test opt-in: consome a API real usando somente fixtures didáticas do projeto."""

import json
from pathlib import Path
import time

from aplicacao.analyzer import analyze_text, explain_code
from aplicacao.gemini_client import GeminiClient
from aplicacao.requisitos import derive_requirements


def main():
    root=Path(__file__).resolve().parents[1]
    source=(root/'testes/arquivos_de_exemplo/cad0001_item_calculo.txt').read_text(encoding='utf-8')
    library=(root/'testes/arquivos_de_exemplo/biblioteca_requisitos.txt').read_text(encoding='utf-8')
    client=GeminiClient()
    results=[]
    for label,operation in (
        ('Documentação',lambda:analyze_text(source,client)),
        ('Explicação',lambda:explain_code(source,client)),
        ('Requisitos e RTM',lambda:derive_requirements(library,client)),
    ):
        start=time.monotonic()
        try:
            result=operation()
            item={'cenario':label,'situacao':'passou','campos_validados':len(result.model_dump())}
        except Exception as exc:
            # Do not print SDK exceptions, credentials, prompts or HTTP headers.
            item={'cenario':label,'situacao':'falhou','tipo':type(exc).__name__}
            from aplicacao.gemini_client import GeminiError
            from aplicacao.analyzer import AnalysisError
            if isinstance(exc,(GeminiError,AnalysisError)):item['mensagem']=str(exc)
        item['segundos']=round(time.monotonic()-start,2)
        results.append(item)
        print(json.dumps(item,ensure_ascii=False),flush=True)
    out=root/'evidencias/gemini_real.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'modelo':client.model,'cenarios':results},ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(r['situacao']=='passou' for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
