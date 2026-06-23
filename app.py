import os
import re
from flask import Flask, render_template, request, Response
from pypdf import PdfReader

app = Flask(__name__)

# Molde Gráfico Padrão Unificado MPM
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

def extrair_texto_simples(arquivo_pdf):
    try:
        leitor = PdfReader(arquivo_pdf)
        texto = ""
        for pagina in leitor.pages:
            texto += pagina.extract_text() + "\n"
        return texto
    except:
        return ""

def estruturar_linhas_html(texto_editor, modo_versao):
    if not texto_editor.strip():
        return ""
    
    linhas = texto_editor.split('\n')
    html_resultado = []
    
    for linha in lines:
        linha = linha.strip()
        if not linha:
            continue
        
        # Processamento de tags customizadas informadas pelo usuário
        # [ALTERADO: texto] -> Fica vermelho itálico se Consolidada, ou Tachado se Alterada
        if "[ALTERADO:" in linha:
            if modo_versao == "alterada":
                linha = re.sub(r'\[ALTERADO:\s*(.*?)\]', r'<span class="tachado-vermelho">\1</span>', linha)
            else:
                linha = re.sub(r'\[ALTERADO:\s*(.*?)\]', r'<span class="alterado-vermelho">(Alterado) \1</span>', linha)
        
        # Identificação de estrutura jurídica para aplicação dos recuos milimétricos
        if re.match(r'^(ART\.|ARTIGO)\s*\d+', linha, re.IGNORECASE):
            linha = re.sub(r'^(ART\.\s*\d+[º\d\w\s\-\.]+|ARTIGO\s*\d+[º\d\w\s\-\.]+)', r'<b>\1</b>', linha, flags=re.IGNORECASE)
            html_resultado.append(f'<div class="artigo">{linha}</div>')
        elif linha.startswith('§') or re.match(r'^(PARÁGRAFO|PARAGRAFO)\s+', linha, re.IGNORECASE):
            html_resultado.append(f'<div class="paragrafo">{linha}</div>')
        else:
            html_resultado.append(f'<div class="preambulo">{linha}</div>')
            
    return '\n'.join(html_resultado)

@app.route('/', methods=['GET', 'POST'])
def index():
    texto_original_extraido = ""
    texto_derivativo_extraido = ""
    
    if request.method == 'POST':
        acao = request.form.get('acao')
        
        # Se a ação for apenas ler os PDFs
        if acao == 'ler_pdfs':
            pdf_orig = request.files.get('pdf_original')
            if pdf_orig:
                texto_original_extraido = extrair_texto_simples(pdf_orig)
            
            pdfs_deriv = request.files.getlist('pdfs_derivativos')
            textos_deriv = []
            for p in pdfs_deriv:
                if p and p.filename != '':
                    textos_deriv.append(f"--- {p.filename} ---\n" + extrair_texto_simples(p))
            texto_derivativo_extraido = "\n".join(textos_deriv)
            
            return render_template('index.html', original=texto_original_extraido, derivativo=texto_derivativo_extraido)
        
        # Se a ação for gerar o HTML final estruturado
        elif acao == 'gerar_html':
            texto_final_revisado = request.form.get('texto_final_revisado')
            nome_ato_original = request.form.get('nome_ato_original', 'Ato Original')
            nome_ato_derivativo = request.form.get('nome_ato_derivativo', 'Ato Modificador')
            link_original = request.form.get('link_original')
            link_derivativo = request.form.get('link_derivativo')
            tipo_versao = request.form.get('tipo_versao')
            
            # Formata Links
            link_original_html = f'<a href="{link_original}" target="_blank">{nome_ato_original}</a>' if link_original else f'<span>{nome_ato_original}</span>'
            links_derivativos_html = f' | <a href="{link_derivativo}" target="_blank">{nome_ato_derivativo}</a>' if link_derivativo else f' | <span>{nome_ato_derivativo}</span>'
            
            # Monta estrutura estrita de parágrafos
            corpo_html = estruturar_linhas_html(texto_final_revisado, tipo_versao)
            
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

    return render_template('index.html', original="", derivativo="")

if __name__ == '__main__':
    app.run(debug=True)
