import os
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
        .relacionamento-links a:hover {{ text-decoration: underline; }}
        .linha-versao {{ border-top: 1px solid #000000; margin-top: 2px; margin-bottom: 15px; }}
        .header-bloco {{ text-align: center; margin-bottom: 25px; }}
        .brasao {{ display: block; margin: 0 auto 10px auto; width: 60pt; height: 60pt; object-fit: contain; }}
        .header-inst {{ font-weight: bold; text-transform: uppercase; font-size: 10pt; line-height: 1.3; }}
        .preambulo {{ text-indent: 1.25cm; margin-bottom: 15px; text-align: justify; }}
        .artigo {{ text-indent: 1.25cm; margin-top: 12px; margin-bottom: 12px; text-align: justify; }}
        .paragrafo {{ text-indent: 1.88cm; margin-top: 8px; margin-bottom: 8px; text-align: justify; }}
        .nota-alterado {{ color: #ff0000; font-style: italic; font-size: 10pt; }}
        .revogado-info {{ color: #000000; }}
        .assinatura {{ text-align: center; margin-top: 50px; page-break-inside: avoid; }}
        .nome {{ font-weight: bold; text-transform: uppercase; }}
        .nota-rodape-bloco {{ margin-top: 40px; border-top: 1px solid #000000; padding-top: 8px; }}
        .nota-rodape {{ font-size: 9.5pt; font-style: italic; text-align: justify; }}
    </style>
</head>
<body>
    <div class="versao-bloco">
        <div class="versao-tag">{tag_versao}</div>
        <div class="relacionamento-links">
            Documentos Relacionados: 
            <a href="{link_original}" target="_blank">{nome_original}</a>
            {links_derivativos_html}
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
    """Função auxiliar que lê o arquivo PDF e extrai o texto contido nele"""
    try:
        leitor = PdfReader(arquivo_pdf)
        texto_completo = ""
        for pagina in leitor.pages:
            texto_completo += pagina.extract_text() + "\n"
        return texto_completo
    except Exception:
        return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Captura as informações de identificação e links do formulário
        ato_original_nome = request.form.get('ato_original_nome')
        link_original = request.form.get('link_original')
        link_derivativo = request.form.get('link_derivativo')
        tipo_versao = request.form.get('tipo_versao')
        
        # 2. Captura o arquivo PDF ÚNICO do Ato Original
        pdf_original = request.files.get('pdf_original')
        texto_ato_original = ""
        if pdf_original and pdf_original.filename != '':
            texto_ato_original = extrair_texto_pdf(pdf_original)

        # 3. Captura UM ou MAIS arquivos PDF dos Atos Derivativos
        pdfs_derivativos = request.files.getlist('pdfs_derivativos')
        textos_derivativos = []
        nomes_derivativos = []
        
        for pdf in pdfs_derivativos:
            if pdf and pdf.filename != '':
                texto_extraido = extrair_texto_pdf(pdf)
                textos_derivativos.append(texto_extraido)
                # Remove a extensão .pdf do nome do arquivo para exibição limpa
                nome_limpo = os.path.splitext(pdf.filename)[0]
                nomes_derivativos.append(nome_limpo)

        # 4. Montagem dos links de documentos relacionados no topo
        texto_atos_derivativos_nome = ", ".join(nomes_derivativos) if nomes_derivativos else "Atos Modificadores"
        links_derivativos_html = ""
        if nomes_derivativos:
            links_derivativos_html = f' | <a href="{link_derivativo}" target="_blank">{texto_atos_derivativos_nome}</a>'

        # 5. Processamento básico do texto (Regras de Negócio)
        # Em produções futuras, criaremos as funções de inteligência de comparação de texto aqui.
        # Por enquanto, ele junta o texto lido estruturando nos blocos CSS dinamicamente.
        corpo_construido = ""
        if texto_ato_original:
            linhas = texto_ato_original.split('\n')
            for linha in lines:
                linha = linha.strip()
                if not linha:
                    continue
                if linha.upper().startswith("ART.") or linha.upper().startswith("ARTIGO"):
                    corpo_construido += f'<div class="artigo"><b>{linha}</b></div>\n'
                elif linha.startswith("§") or linha.upper().startswith("PARÁGRAFO"):
                    corpo_construido += f'<div class="paragrafo">{linha}</div>\n'
                else:
                    corpo_construido += f'<div class="preambulo">{linha}</div>\n'
        else:
            corpo_construido = '<div class="artigo"><b>Art. 1º</b> [Nenhum texto pôde ser extraído ou o arquivo PDF original estava vazio].</div>'

        # 6. Define as Tags de Versão baseadas nas escolhas
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Alterada - {ato_original_nome}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Consolidada - {ato_original_nome}"

        # 7. Preenche o molde HTML oficial do padrão MPM unificado
        html_final = MODELO_HTML_ESTRITO.format(
            titulo_documento=titulo,
            tag_versao=tag,
            link_original=link_original,
            nome_original=ato_original_nome,
            links_derivativos_html=links_derivativos_html,
            corpo_texto=corpo_construido
        )
        
        # Dispara o download do arquivo .html gerado
        return Response(
            html_final,
            mimetype="text/html",
            headers={"Content-disposition": f"attachment; filename={tipo_versao}_consolidada.html"}
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
