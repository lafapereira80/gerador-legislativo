import os
import re
from flask import Flask, render_template, request, Response
from pypdf import PdfReader
from google import genai
from google.genai import types

app = Flask(__name__)

# Configura a IA usando a chave que você vai cadastrar no Render
# Se não achar a chave, tenta ler uma string vazia para não derrubar o servidor imediatamente
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Matriz Gráfica Estrita Homologada (Padrão MPM)
MODELO_HTML_ESTRITO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{titulo_documento}</title>
    <style>
        @page {{ size: A4; margin: 25mm 20mm 20mm 25mm; }}
        body {{
            font-family: 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #000000;
            text-align: justify;
            background-color: #ffffff;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20px;
        }}
        .versao-bloco {{ margin-bottom: 20px; }}
        .versao-tag {{ font-weight: bold; font-size: 10pt; color: #000000; text-align: left; padding-bottom: 5px; }}
        .relacionamento-links {{ font-size: 9.5pt; color: #555555; text-align: left; padding-bottom: 5px; }}
        .relacionamento-links a {{ color: #0066cc; text-decoration: none; font-weight: bold; }}
        .linha-versao {{ border-top: 1px solid #000000; margin-top: 2px; margin-bottom: 15px; }}
        .header-bloco {{ text-align: center; margin-bottom: 25px; }}
        .brasao {{ display: block; margin: 0 auto 10px auto; width: 60pt; height: 60pt; object-fit: contain; }}
        .header-inst {{ font-weight: bold; text-transform: uppercase; font-size: 10pt; line-height: 1.3; margin-bottom: 30px; }}
        .preambulo {{ text-indent: 1.25cm; margin-top: 12px; margin-bottom: 12px; text-align: justify; }}
        .artigo {{ text-indent: 1.25cm; margin-top: 14px; margin-bottom: 14px; text-align: justify; }}
        .paragrafo {{ text-indent: 1.88cm; margin-top: 10px; margin-bottom: 10px; text-align: justify; }}
        .alterado-vermelho {{ color: #ff0000; font-style: italic; }}
        .tachado-vermelho {{ text-decoration: line-through; color: #ff0000; }}
        .nota-rodape-bloco {{ margin-top: 50px; border-top: 1px solid #000000; padding-top: 8px; }}
        .nota-rodape {{ font-size: 9.5pt; font-style: italic; text-align: justify; color: #444444; }}
    </style>
</head>
<body>
    <div class="versao-bloco">
        <div class="versao-tag">{tag_versao}</div>
        <div class="relacionamento-links">
            Documentos Relacionados: {link_original_html}{links_derivativos_html}
        </div>
        <div class="linha-versao"></div>
    </div>
    
    <div class="header-bloco">
        <img class="brasao" src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Coat_of_arms_of_Brazil.svg" alt="Brasão da República">
        <div class="header-inst">
            MINISTÉRIO PÚBLICO DA UNIÃO<br>
            MINISTÉRIO PÚBLICO MILITAR<br>
            PROCURADORIA-GERAL DE JUSTIÇA MILITAR
        </div>
    </div>

    {corpo_texto}

    <div class="nota-rodape-bloco">
        <div class="nota-rodape"><strong>Nota:</strong> Este documento possui caráter estritamente consultivo e informativo, não substituindo o texto original publicado no Boletim de Serviço Eletrônico (BSe) ou no Diário Oficial.</div>
    </div>
</body>
</html>"""

def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PdfReader(arquivo_pdf)
        texto = ""
        for pagina in leitor.pages:
            texto += pagina.extract_text() + "\n"
        return texto
    except:
        return ""

def pedir_fusao_ao_gemini(texto_original, texto_derivativo, modo_versao):
    """Envia os textos para o modelo analítico do Gemini realizar a fusão legislativa real"""
    if not API_KEY:
        return '<div class="artigo"><b>Erro:</b> A chave de API do Gemini (GEMINI_API_KEY) não foi configurada no Render.</div>'
    
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        Você é um especialista em engenharia documental jurídica e técnica legislativa.
        Sua tarefa é ler o texto de um "Ato Original" e aplicar as modificações trazidas pelo "Ato Derivativo" obedecendo rigorosamente o escopo solicitado.

        TEXTO DO ATO ORIGINAL:
        \"\"\"{texto_original}\"\"\"

        TEXTO DO ATO DERIVATIVO (MODIFICADOR):
        \"\"\"{texto_derivativo}\"\"\"

        TIPO DE VERSÃO EXIGIDA: {modo_versao.upper()}

        REGRAS DE CONTEÚDO E FUSÃO:
        1. Identifique quais artigos, parágrafos ou incisos do Ato Original foram alterados ou revogados pelo Ato Derivativo.
        2. Se o tipo for VERSAO CONSOLIDADA: Substitua o texto antigo pelo novo texto diretamente. Ao final do trecho alterado, adicione obrigatoriamente a expressão entre parágrafos vermelhos informando a mudança, usando a tag <span class="alterado-vermelho">(Redação dada pelo Ato Modificador)</span>.
        3. Se o tipo for VERSAO ALTERADA: Mantenha o texto antigo/original, mas envolva-o completamente na tag <span class="tachado-vermelho">texto antigo aqui</span> e insira logo à frente o novo texto modificado envolvido na tag <span class="alterado-vermelho">texto novo aqui</span>.
        4. Identifique automaticamente na primeira linha significativa de cada documento o Nome Oficial do Ato (Ex: Portaria nº 130/PGJM, de 2022). Seus primeiros outputs devem focar em extrair esses nomes limpos.

        REGRAS ESTREITAS DE FORMATAÇÃO HTML (Obrigatório):
        - Seu output final deve conter APENAS as tags do corpo do texto que substituem os artigos. Não invente blocos, cabeçalhos ou rodapés.
        - Toda linha correspondente a um Artigo (ex: Art. 1º, Art. 22) deve ser envelopada estritamente em: <div class="artigo"><b>Art. Xº</b> Resto do texto...</div>
        - Toda linha correspondente a um Parágrafo (ex: § 1º, Parágrafo único) deve ser envelopada estritamente em: <div class="paragrafo">§ Xº Resto do texto...</div>
        - Textos de preâmbulo, ementas, assinaturas ou considerandos devem ser envelopados em: <div class="preambulo">Texto aqui...</div>
        - Não use Markdown (```html) na resposta. Devolva texto puro contendo apenas as marcações das divs mencionadas.
        """

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f'<div class="artigo"><b>Erro no processamento da IA:</b> {str(e)}</div>'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        link_original = request.form.get('link_original')
        link_derivativo = request.form.get('link_derivativo')
        tipo_versao = request.form.get('tipo_versao')
        
        pdf_orig = request.files.get('pdf_original')
        pdf_derivs = request.files.getlist('pdfs_derivativos')
        
        if not pdf_orig or pdf_orig.filename == '':
            return "Erro: O PDF do Ato Original é obrigatório.", 400

        # Extração de textos cruas do PDF
        texto_original = extrair_texto_pdf(pdf_orig)
        
        textos_modificadores = []
        for p in pdf_derivs:
            if p and p.filename != '':
                textos_modificadores.append(extrair_texto_pdf(p))
        texto_modificador_consolidado = "\n".join(textos_modificadores)

        # Chamar o motor de inteligência artificial para ler e consolidar os textos de verdade
        corpo_html = pedir_fusao_ao_gemini(texto_original, texto_modificador_consolidado, tipo_versao)

        # Algoritmo auxiliar para tentar ler nomes de exibição amigáveis no topo do HTML
        linhas_orig = [l.strip() for l in texto_original.split('\n') if l.strip()]
        ato_original_nome = linhas_orig[0][:75] if linhas_orig else "Ato Original"
        nome_ato_derivativo = "Atos Modificadores"

        # Montagem dinâmica de links
        link_original_html = f'<a href="{link_original}" target="_blank">{ato_original_nome}</a>' if link_original else f'<span>{ato_original_nome}</span>'
        links_derivativos_html = f' | <a href="{link_derivativo}" target="_blank">{nome_ato_derivativo}</a>' if link_derivativo else f' | <span>{nome_ato_derivativo}</span>'
        
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas por: {nome_ato_derivativo}"
            titulo = f"Versão Alterada - {ato_original_nome}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas por: {nome_ato_derivativo}"
            titulo = f"Versão Consolidada - {ato_original_nome}"
            
        html_final = MODELO_HTML_ESTRITO.format(
            titulo_documento=titulo,
            tag_versao=tag,
            link_original_html=link_original_html,
            links_derivativos_html=links_derivativos_html,
            corpo_texto=corpo_html
        )
        
        return Response(
            html_final,
            mimetype="text/html",
            headers={"Content-disposition": f"attachment; filename={tipo_versao}_consolidada.html"}
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
