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
    </style>
</head>
<body>
    <div class="versao-bloco">
        <div class="versao-tag">{tag_versao}</div>
        <div class="relacionamento-links">
            Documentos Relacionados: 
            {link_original_html}
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
</body>
</html>"""

def extrair_texto_pdf(arquivo_pdf):
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
        link_original = request.form.get('link_original')
        link_derivativo = request.form.get('link_derivativo')
        tipo_versao = request.form.get('tipo_versao')
        
        # 1. Processa o PDF do Ato Original
        pdf_original = request.files.get('pdf_original')
        texto_ato_original = ""
        ato_original_nome = "Ato Original"
        
        if pdf_original and pdf_original.filename != '':
            texto_ato_original = extrair_texto_pdf(pdf_original)
            # Tenta capturar a primeira linha preenchida do PDF como nome da portaria
            linhas_original = [l.strip() for l in texto_ato_original.split('\n') if l.strip()]
            if linhas_original:
                # Limita o tamanho do nome extraído para não quebrar o layout
                ato_original_nome = linhas_original[0][:80] 
            else:
                ato_original_nome = os.path.splitext(pdf_original.filename)[0]

        # 2. Processa os PDFs dos Atos Derivativos
        pdfs_derivativos = request.files.getlist('pdfs_derivativos')
        nomes_derivativos = []
        
        for pdf in pdfs_derivativos:
            if pdf and pdf.filename != '':
                texto_extraido = extrair_texto_pdf(pdf)
                linhas_derivativo = [l.strip() for l in texto_extraido.split('\n') if l.strip()]
                if linhas_derivativo:
                    nomes_derivativos.append(linhas_derivativo[0][:80])
                else:
                    nomes_derivativos.append(os.path.splitext(pdf.filename)[0])

        texto_atos_derivativos_nome = ", ".join(nomes_derivativos) if nomes_derivativos else "Atos Modificadores"

        # 3. Montagem inteligente dos links (Se o usuário não preencher, mostra apenas o texto)
        if link_original and link_original.strip():
            link_original_html = f'<a href="{link_original}" target="_blank">{ato_original_nome}</a>'
        else:
            link_original_html = f'<span>{ato_original_nome}</span>'

        links_derivativos_html = ""
        if nomes_derivativos:
            if link_derivativo and link_derivativo.strip():
                links_derivativos_html = f' | <a href="{link_derivativo}" target="_blank">{texto_atos_derivativos_nome}</a>'
            else:
                links_derivativos_html = f' | <span>{texto_atos_derivativos_nome}</span>'

        # 4. Montagem estruturada do texto
        corpo_construido = ""
        if texto_ato_original:
            linhas = texto_ato_original.split('\n')
            for linha in linhas:
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
            corpo_construido = '<div class="artigo"><b>Art. 1º</b> [Nenhum texto pôde ser extraído do arquivo PDF enviado].</div>'

        # 5. Define Tags e Título
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Alterada - {ato_original_nome}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Consolidada - {ato_original_nome}"

        # 6. Renderização final do Molde Estrito
        html_final = MODELO_HTML_ESTRITO.format(
            titulo_documento=titulo,
            tag_versao=tag,
            link_original_html=link_original_html,
            links_derivativos_html=links_derivativos_html,
            corpo_texto=corpo_construido
        )
        
        return Response(
            html_final,
            mimetype="text/html",
            headers={"Content-disposition": f"attachment; filename={tipo_versao}_consolidada.html"}
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
