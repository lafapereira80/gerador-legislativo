import os
import re
from flask import Flask, render_template, request, Response
from pypdf import PdfReader

app = Flask(__name__)

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
        # Remove quebras de linha artificiais para juntar as frases perfeitamente
        return re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
    except:
        return ""

def extrair_nome_ato(texto):
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    for linha in linhas:
        if re.search(r'(PORTARIA|RESOLUÇÃO|ATO|DECRETO|LEI)\s+(Nº|N°|O|P)', linha, re.IGNORECASE):
            return linha[:75]
    return linhas[0][:75] if linhas else "Ato Não Identificado"

def analisar_e_funder_textos(texto_orig, texto_mod, modo_versao):
    """Algoritmo de IA Analítica: Mapeia modificações e faz o merge automático"""
    linhas_orig = [l.strip() for l in texto_orig.split('\n') if l.strip()]
    
    # Procura padrões de alteração no texto modificador (ex: Art. 1º passa a vigorar...)
    modificacoes = {}
    padrao_altera = r'(?:alterar|altera|vigorar|passa a vigorar).*?(Art\.\s*\d+)'
    
    # Varredura simples para simular inteligência de fusão baseada em referências cruzadas
    matches = re.findall(padrao_altera, texto_mod, re.IGNORECASE)
    for m in matches:
        art_alvo = m.strip()
        # Captura o parágrafo ou linha do modificador que cita o artigo novo
        linhas_mod = texto_mod.split('\n')
        for l_m in linhas_mod:
            if art_alvo.lower() in l_m.lower() and len(l_m) > 30:
                modificacoes[art_alvo.lower()] = l_m.strip()

    html_resultado = []
    for linha in linhas_orig:
        art_encontrado = None
        # Verifica se esta linha original sofreu modificação detectada no texto derivativo
        for art_chave in modificacoes.keys():
            if art_chave in linha.lower():
                art_encontrado = art_chave
                break
        
        if art_encontrado:
            texto_novo = modificacoes[art_encontrado]
            if modo_versao == "alterada":
                linha_final = f'<span class="tachado-vermelho">{linha}</span> <span class="alterado-vermelho">{texto_novo}</span>'
            else:
                linha_final = f'<span class="alterado-vermelho">{texto_novo} (NR)</span>'
        else:
            linha_final = linha

        # Formatação estrutural estrita
        if re.match(r'^(ART\.|ARTIGO)\s*\d+', linha_final, re.IGNORECASE):
            linha_final = re.sub(r'^(ART\.\s*\d+[º\d\w\s\-\.]+|ARTIGO\s*\d+[º\d\w\s\-\.]+)', r'<b>\1</b>', linha_final, flags=re.IGNORECASE)
            html_resultado.append(f'<div class="artigo">{linha_final}</div>')
        elif linha_final.startswith('§') or re.match(r'^(PARÁGRAFO|PARAGRAFO)\s+', linha_final, re.IGNORECASE):
            html_resultado.append(f'<div class="paragrafo">{linha_final}</div>')
        else:
            html_resultado.append(f'<div class="preambulo">{linha_final}</div>')

    return '\n'.join(html_resultado)

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

        texto_original = extrair_texto_pdf(pdf_orig)
        nome_ato_original = extrair_nome_ato(texto_original)
        
        textos_modificadores = []
        nomes_modificadores = []
        for p in pdf_derivs:
            if p and p.filename != '':
                txt_m = extrair_texto_pdf(p)
                textos_modificadores.append(txt_m)
                nomes_modificadores.append(extrair_nome_ato(txt_m))
        
        texto_modificador_consolidado = "\n".join(textos_modificadores)
        nome_ato_derivativo = ", ".join(nomes_modificadores) if nomes_modificadores else "Atos Modificadores"

        # Montagem automática dos links
        link_original_html = f'<a href="{link_original}" target="_blank">{nome_ato_original}</a>' if link_original else f'<span>{nome_ato_original}</span>'
        links_derivativos_html = f' | <a href="{link_derivativo}" target="_blank">{nome_ato_derivativo}</a>' if link_derivativo else f' | <span>{nome_ato_derivativo}</span>'
        
        # Executa a Fusão e Inteligência Analítica de Texto
        corpo_html = analisar_e_funder_textos(texto_original, texto_modificador_consolidado, tipo_versao)
        
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas por: {nome_ato_derivativo}"
            titulo = f"Versão Alterada - {nome_ato_original}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas por: {nome_ato_derivativo}"
            titulo = f"Versão Consolidada - {nome_ato_original}"
            
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
