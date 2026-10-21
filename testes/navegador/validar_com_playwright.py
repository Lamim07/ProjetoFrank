"""python -m testes.navegador.validar_com_playwright; sobe e encerra servidores locais."""

import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen
from importlib.metadata import version

from playwright.sync_api import sync_playwright, expect
expect.set_options(timeout=20000)

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('TESTINGSTUDIO_E2E_OUTPUT', ROOT/'evidencias'/'playwright'))
FIXTURE = ROOT/'testes/arquivos_de_exemplo/cad0001_item_calculo.txt'
LIBRARY = ROOT/'testes/arquivos_de_exemplo/biblioteca_requisitos.txt'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


class ProjectBrowserValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        cls.processes=[]
        cls.logs=[]
        cls.records=[]
        cls.playwright=None
        try:
            cls.urls=[]
            for entry in ('app.py','testes/navegador/app_simulado.py'):
                chosen=port()
                log=open(OUT/(Path(entry).stem+'.log'),'w',encoding='utf-8')
                cls.logs.append(log)
                env=dict(os.environ)
                env.pop('GEMINI_API_KEY',None)
                env['PYTHONDONTWRITEBYTECODE']='1'
                command=[sys.executable,'-m','streamlit','run',str(ROOT/entry),'--server.address','127.0.0.1',
                         '--server.port',str(chosen),'--server.headless','true','--browser.gatherUsageStats','false']
                process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
                cls.processes.append(process)
                url=f'http://127.0.0.1:{chosen}'
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Servidor de validação encerrou; consulte o log local.')
                    try:
                        with urlopen(url+'/_stcore/health',timeout=1) as response:
                            if response.status==200:break
                    except Exception:time.sleep(.2)
                else:raise RuntimeError('Servidor local não iniciou dentro de 45 segundos.')
                cls.urls.append(url)
            cls.playwright=sync_playwright().start()
            cls.browser=cls.playwright.chromium.launch(headless=True)
        except Exception:
            cls.cleanup()
            raise

    @classmethod
    def cleanup(cls):
        if getattr(cls,'playwright',None):
            if hasattr(cls,'browser'):cls.browser.close()
            cls.playwright.stop()
        for process in cls.processes:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)
        for log in cls.logs:log.close()

    @classmethod
    def tearDownClass(cls):
        try:
            report={'python':platform.python_version(),'playwright':version('playwright'),
                    'navegador':cls.browser.version,'gemini':'Simulado nos cenários de sucesso E2E; sem chave no servidor de produção de teste.',
                    'cenarios':cls.records}
            (OUT/'resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        finally:cls.cleanup()

    def setUp(self):
        self.started=time.monotonic()
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        self.page=self.context.new_page()
        self.page.set_default_timeout(20000)
        self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))

    def tearDown(self):
        # Individual result is recorded from outcomes added during this test only.
        test_id=self.id()
        failed=any(test.id()==test_id for test,_ in self._outcome.result.failures+self._outcome.result.errors)
        name=self._testMethodName
        screenshot=OUT/(name+'.png')
        try:
            self.page.screenshot(path=str(screenshot),full_page=False)
            if not failed:
                self.assertFalse(self.errors,'Erros JavaScript na página: '+str(self.errors))
                expect(self.page.get_by_test_id('stException')).to_have_count(0)
        except Exception:
            failed=True
            raise
        finally:
            self.records.append({'cenario':name,'situacao':'falhou' if failed or self.errors else 'passou',
                                 'segundos':round(time.monotonic()-self.started,2),'captura':screenshot.name})
            self.context.close()

    def open(self,simulated=False,fixture=FIXTURE):
        self.page.goto(self.urls[int(simulated)])
        expect(self.page.get_by_role('heading',name='Entenda o que há no seu TXT')).to_be_visible()
        if fixture:
            self.page.locator('input[type=file]').set_input_files(str(fixture))
            expect(self.page.get_by_role('radio',name='PCE / AVL',exact=True)).to_be_visible()
        self.settle()

    def settle(self):
        expect(self.page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning',timeout=20000)

    def mode(self,label):
        # React Aria hides the native input under the visible label.
        self.page.get_by_text(label,exact=True).click()
        expect(self.page.get_by_role('radio',name=label,exact=True)).to_be_checked()
        headings={'PCE / AVL':'Classes de equivalência e valores limite',
                  'Fluxo de controle':'Grafo de fluxo e complexidade ciclomática',
                  'Pares Def-Uso':'Pares Def-Uso','Mutação':'Mutação e eficácia dos testes',
                  'Requisitos e RTM':'Requisitos, casos de uso e rastreabilidade'}
        if label in headings:expect(self.page.get_by_role('heading',name=headings[label],exact=True)).to_be_visible()
        self.settle()

    def button(self,label):
        self.page.get_by_role('button',name=label,exact=True).click()

    def download(self,label):
        with self.page.expect_download() as pending:self.button(label)
        result=pending.value
        destination=OUT/(self._testMethodName+'_'+result.suggested_filename)
        result.save_as(destination)
        return destination

    def pdf(self):
        self.button('Transformar em PDF')
        path=self.download('Baixar PDF')
        self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
        self.assertGreater(path.stat().st_size,1000)

    def test_01_upload_errors_and_missing_key(self):
        self.open(fixture=None)
        uploader=self.page.locator('input[type=file]')
        uploader.set_input_files({'name':'vazio.txt','mimeType':'text/plain','buffer':b''})
        expect(self.page.get_by_text('O arquivo está vazio. Envie um TXT com conteúdo.',exact=True)).to_be_visible()
        uploader.set_input_files({'name':'invalido.txt','mimeType':'text/plain','buffer':b'\xff\xfe'})
        expect(self.page.get_by_test_id('stAlert').filter(has_text='UTF-8')).to_be_visible()
        uploader.set_input_files(str(FIXTURE))
        self.button('Gerar documentação')
        expect(self.page.get_by_test_id('stAlert').filter(has_text='A chave Gemini não está configurada')).to_be_visible()

    def test_02_sprint1_black_box(self):
        self.open()
        self.mode('PCE / AVL')
        expect(self.page.get_by_role('textbox',name='Limite mínimo',exact=True)).to_have_count(3)
        expect(self.page.get_by_role('textbox',name='Limite máximo',exact=True)).to_have_count(3)
        for field in self.page.get_by_role('textbox',name='Limite mínimo',exact=True).all():field.fill('0')
        for field in self.page.get_by_role('textbox',name='Limite máximo',exact=True).all():field.fill('100')
        self.page.get_by_role('textbox',name='Fórmula do resultado esperado (opcional)',exact=True).fill('(p_val1*p_val2)+p_val3')
        self.button('Gerar PCE, AVL e casos de teste')
        expect(self.page.get_by_text('Confirme os critérios antes de gerar os casos.',exact=True)).to_be_visible()
        self.page.get_by_role('checkbox',name='Confirmo que os limites',exact=False).press('Space')
        self.button('Gerar PCE, AVL e casos de teste')
        expect(self.page.get_by_role('heading',name='Plano de testes funcionais')).to_be_visible()
        data=json.loads(self.download('Baixar casos de teste (.json)').read_text(encoding='utf-8'))
        self.assertEqual(len(data['criterios']),3)
        self.assertTrue(any(r['valor']=='-0.01' for r in data['limites']))
        self.assertTrue(any(r['valor']=='100.01' for r in data['limites']))
        self.pdf()

    def test_03_sprint2_white_box(self):
        self.open();self.mode('Fluxo de controle');self.button('Gerar grafo e métricas')
        expect(self.page.get_by_text('Complexidade ciclomática V(G)',exact=True)).to_be_visible()
        combo=self.page.get_by_role('combobox',name='Função para visualizar')
        combo.fill('cad0001_calcula_valor')
        combo.press('ArrowDown')
        combo.press('Enter')
        expect(self.page.get_by_test_id('stMetricValue')).to_have_text('4')
        dot=self.download('Baixar grafo (.dot)').read_text(encoding='utf-8')
        self.assertIn('digraph fluxo',dot)
        self.assertIn('p_val1 IS NULL',dot)
        self.pdf()

    def test_04_sprint3_data_flow(self):
        self.open();self.mode('Pares Def-Uso');self.button('Analisar definições e usos')
        data=json.loads(self.download('Baixar Def-Uso (.json)').read_text(encoding='utf-8'))
        self.assertEqual(len(data['functions'][0]['pairs']),13)
        self.assertEqual(len(data['unsupported']),4)
        self.pdf()

    def test_05_sprint3_mutant_catalog(self):
        self.open();self.mode('Mutação');self.button('Gerar catálogo de mutantes')
        variant=self.download('Baixar variante TXT').read_text(encoding='utf-8')
        self.assertNotEqual(variant,FIXTURE.read_text(encoding='utf-8'))
        data=json.loads(self.download('Baixar campanha (.json)').read_text(encoding='utf-8'))
        self.assertEqual(len(data['mutantes']),24)
        self.assertIsNone(data['escore']['escore_final'])
        self.pdf()

    def test_06_sprint3_source_mutation(self):
        self.open();self.mode('Mutação')
        self.page.get_by_role('tab',name='Mutação da função',exact=True).click()
        csv='p_val1,p_val2,p_val3,Esperado\n2,3,4,10\nNULL,3,4,4\n2,NULL,4,4\n2,3,NULL,6\nNULL,NULL,NULL,0'
        self.page.get_by_role('textbox',name='Casos para a função (CSV)',exact=True).fill(csv)
        self.page.get_by_role('checkbox',name='Confirmei as entradas',exact=False).press('Space')
        self.button('Avaliar mutantes da função')
        data=json.loads(self.download('Baixar avaliação da função (.json)').read_text(encoding='utf-8'))
        self.assertEqual((data['total'],data['mortos'],data['escore']),(9,9,100))
        self.pdf()
        self.page.get_by_test_id('stMetric').scroll_into_view_if_needed()
        self.page.screenshot(path=str(OUT/'sprint3_mutacao_funcao.png'))
        self.page.get_by_role('textbox',name='Casos para a função (CSV)',exact=True).fill(csv.replace('2,3,4,10','2,3,4,11'))
        self.button('Avaliar mutantes da função')
        expect(self.page.get_by_test_id('stAlert').filter(has_text='Corrija a base')).to_be_visible()
        expect(self.page.get_by_role('button',name='Baixar avaliação da função (.json)',exact=True)).to_have_count(0)

    def test_07_arithmetic_experiment(self):
        self.open();self.mode('Mutação')
        self.page.get_by_role('tab',name='Experimento aritmético',exact=True).click()
        expect(self.page.get_by_role('textbox',name='Fórmula aritmética a avaliar',exact=True)).to_have_value('(p_val1 * p_val2) + p_val3')
        self.page.get_by_role('textbox',name='Casos da fórmula (CSV)',exact=True).fill('p_val1,p_val2,p_val3,Esperado\n2,3,4,10')
        self.page.get_by_role('checkbox',name='Confirmo a fórmula e os resultados esperados',exact=False).press('Space')
        self.button('Avaliar mutações da fórmula')
        data=json.loads(self.download('Baixar experimento (.json)').read_text(encoding='utf-8'))
        self.assertEqual(data['escore'],100)
        self.pdf()

    def test_08_documentation_and_explanation_simulated(self):
        self.open(simulated=True)
        self.button('Gerar documentação')
        expect(self.page.get_by_role('heading',name='Documentação do arquivo')).to_be_visible()
        self.assertIn('Multiplica',self.download('Baixar documentação (.md)').read_text(encoding='utf-8'))
        self.pdf()
        self.mode('Explicar o código');self.button('Explicar código')
        expect(self.page.get_by_role('heading',name='Como o código funciona')).to_be_visible()
        self.pdf()

    def test_09_requirements_review_and_rtm_simulated(self):
        self.open(simulated=True,fixture=LIBRARY);self.mode('Requisitos e RTM')
        self.button('Derivar requisitos e casos de teste')
        self.page.get_by_role('checkbox',name='Revisei os requisitos',exact=False).press('Space')
        self.button('Aplicar revisão e atualizar RTM')
        expect(self.page.get_by_text('Revisão registrada. Os casos de teste aguardam execução.',exact=True)).to_be_visible()
        data=json.loads(self.download('Baixar proposta e RTM (.json)').read_text(encoding='utf-8'))
        self.assertTrue(data['revisao_registrada']);self.assertEqual(len(data['rtm_requisitos_testes']),5)
        self.assertIn(b'REQ01',self.download('Baixar matriz RTM (.csv)').read_bytes())
        self.pdf()

    def test_10_service_failure_simulated(self):
        self.open(simulated=True)
        self.page.locator('input[type=file]').set_input_files({'name':'falha.txt','mimeType':'text/plain','buffer':b'FALHA_GEMINI'})
        expect(self.page.get_by_text('falha.txt ·',exact=False)).to_be_visible()
        self.button('Gerar documentação')
        expect(self.page.get_by_text('Serviço Gemini simulado indisponível. Tente novamente.',exact=True)).to_be_visible()

    def test_11_session_isolation_and_changed_file(self):
        self.open();self.mode('Fluxo de controle');self.button('Gerar grafo e métricas')
        expect(self.page.get_by_role('button',name='Baixar grafo (.dot)',exact=True)).to_be_visible()
        other=self.context.browser.new_context()
        try:
            page=other.new_page();page.goto(self.urls[0])
            expect(page.get_by_text('Selecione um .txt para começar.',exact=True)).to_be_visible()
            expect(page.get_by_role('button',name='Baixar grafo (.dot)',exact=True)).to_have_count(0)
        finally:other.close()
        self.page.locator('input[type=file]').set_input_files({'name':'novo.txt','mimeType':'text/plain','buffer':b'Novo conteudo'})
        expect(self.page.get_by_text('novo.txt ·',exact=False)).to_be_visible()
        expect(self.page.get_by_role('button',name='Baixar grafo (.dot)',exact=True)).to_have_count(0)

    def test_12_mobile_layout(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.open();self.mode('Mutação')
        self.page.get_by_role('tab',name='Mutação da função',exact=True).click()
        expect(self.page.get_by_role('textbox',name='Casos para a função (CSV)',exact=True)).to_be_visible()
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),400)


if __name__=='__main__':unittest.main(verbosity=2)
