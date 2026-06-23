import os
import re
from flask import Flask, render_template, request, Response
from pypdf import PdfReader

app = Flask(__name__)

# Matriz Gráfica Homologada e Estrita (Padrão MPM - Unificado)
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
        .header-inst {{ font-weight: bold; text-transform: uppercase; font-size: 10pt; line-height: 1.3; margin-bottom: 30px; }}
        .preambulo {{ text-indent: 1.25cm; margin-top: 12px; margin-bottom: 12px; text-align: justify; }}
        .artigo {{ text-indent: 1.25cm; margin-top: 14px; margin-bottom: 14px; text-align: justify; }}
        .paragrafo {{ text-indent: 1.88cm; margin-top: 10px; margin-bottom: 10px; text-align: justify; }}
        .nota-alterado {{ color: #ff0000; font-style: italic; font-size: 10pt; }}
        .alterado-antigo {{ text-decoration: line-through; color: #ff0000; }}
        .nota-rodape-bloco {{ margin-top: 50px; border-top: 1px solid #000000; padding-top: 8px; }}
        .nota-rodape {{ font-size: 9.5pt; font-style: italic; text-align: justify; color: #444444; }}
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

    <div class="nota-rodape-bloco">
        <div class="nota-rodape"><strong>Nota:</strong> Este documento possui caráter estritamente consultivo e informativo, não substituindo o texto original publicado no Boletim de Serviço Eletrônico (BSe) ou no Diário Oficial.</div>
    </div>
</body>
</html>"""

def extrair_e_limpar_texto(arquivo_pdf):
    """Extrai o texto eliminando quebras de linha órfãs que quebram a simetria gráfica"""
    try:
        leitor = PdfReader(arquivo_pdf)
        texto_completo = ""
        for pagina in leitor.pages:
            texto_completo += pagina.extract_text() + "\n"
        
        # Junta linhas separadas por quebras simples para remontar parágrafos contínuos
        texto_limpo = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto_completo)
        return texto_limpo
    except Exception:
        return ""

def estruturar_em_html(texto_bruto):
    """Aplica as classes CSS de recuo e peso de fonte segundo a técnica legislativa"""
    if not texto_bruto.strip():
        return '<div class="artigo"><b>Art. 1º</b> [Nenhum texto pôde ser extraído do arquivo PDF].</div>'
    
    blocos = texto_bruto.split('\n')
    html_processado = []
    
    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue
        
        # Identifica Artigos (Ex: Art. 1º, Artigo 12)
        if re.match(r'^(ART\.|ARTIGO)\s*\d+', bloco, re.IGNORECASE):
            # Deixa o início do artigo em negrito
            bloco_formatado = re.sub(r'^(ART\.\s*\d+[º\d\w\s\-\.]+|ARTIGO\s*\d+[º\d\w\s\-\.]+)', r'<b>\1</b>', bloco, flags=re.IGNORECASE)
            html_processado.append(f'<div class="artigo">{bloco_formatado}</div>')
        
        # Identifica Parágrafos (Ex: § 1º, Parágrafo único)
        elif bloco.startswith('§') or re.match(r'^(PARÁGRAFO|PARAGRAFO)\s+', bloco, re.IGNORECASE):
            html_processado.append(f'<div class="paragrafo">{bloco}</div>')
            
        # O restante entra como preâmbulo/texto explicativo
        else:
            html_processado.append(f'<div class="preambulo">{bloco}</div>')
            
    return '\n'.join(html_processado)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        link_original = request.form.get('link_original')
        link_derivativo = request.form.get('link_derivativo')
        tipo_versao = request.form.get('tipo_versao')
        
        # 1. Processamento e Leitura Limpa do Ato Original
        pdf_original = request.files.get('pdf_original')
        texto_ato_original = ""
        ato_original_nome = "Ato Original"
        
        if pdf_original and pdf_original.filename != '':
            texto_ato_original = extrair_e_limpar_texto(pdf_original)
            
            # Tenta capturar a primeira frase/linha significativa para dar nome à portaria
            linhas_nome = [l.strip() for l in texto_ato_original.split('\n') if l.strip()]
            if linhas_nome:
                ato_original_nome = linhas_nome[0][:75]
            else:
                ato_original_nome = os.path.splitext(pdf_original.filename)[0]

        # 2. Processamento e Leitura dos Atos Derivativos (Modificadores)
        pdfs_derivativos = request.files.getlist('pdfs_derivativos')
        nomes_derivativos = []
        
        for pdf in pdfs_derivativos:
            if pdf and pdf.filename != '':
                texto_derivativo = extrair_e_limpar_texto(pdf)
                linhas_derivativo = [l.strip() for l in texto_derivativo.split('\n') if l.strip()]
                if linhas_derivativo:
                    nomes_derivativos.append(linhas_derivativo[0][:75])
                else:
                    nomes_derivativos.append(os.path.splitext(pdf.filename)[0])

        texto_atos_derivativos_nome = ", ".join(nomes_derivativos) if nomes_derivativos else "Atos Modificadores"

        # 3. Formatação dos Links de Relacionamento no Topo
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

        # 4. Geração do Corpo do Texto Rigorosamente Formatado
        corpo_final_html = estruturar_em_html(texto_ato_original)

        # 5. Definição estrita das Tags superiores
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Alterada - {ato_original_nome}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas por: {texto_atos_derivativos_nome}"
            titulo = f"Versão Consolidada - {ato_original_nome}"

        # 6. Injeção final de dados no Molde Oficial
        html_final = MODELO_HTML_ESTRITO.format(
            titulo_documento=titulo,
            tag_versao=tag,
            link_original_html=link_original_html,
            links_derivativos_html=links_derivativos_html,
            corpo_texto=corpo_final_html
        )
        
        return Response(
            html_final,
            mimetype="text/html",
            headers={"Content-disposition": f"attachment; filename={tipo_versao}_consolidada.html"}
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
