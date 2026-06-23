import os
from flask import Flask, render_template, request, Response

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
            <a href="{link_original}" target="_blank">{nome_original}</a> | 
            <a href="{link_derivativo}" target="_blank">{nome_derivativo}</a>
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ato_original = request.form.get('ato_original')
        link_original = request.form.get('link_original')
        ato_derivativo = request.form.get('ato_derivativo')
        link_derivativo = request.form.get('link_derivativo')
        tipo_versao = request.form.get('tipo_versao')
        
        corpo_construido = f"""
        <div class="preambulo">O <b>PROCURADOR-GERAL DE JUSTIÇA MILITAR</b>, no uso de suas atribuições... <b>resolve:</b></div>
        <div class="artigo"><b>Art. 1º</b> Documento gerado com sucesso para o ato: {ato_original}.</div>
        <div class="paragrafo">Parágrafo único. Modificações processadas com base no ato derivativo.</div>
        """
        
        if tipo_versao == "alterada":
            tag = f"VERSÃO ALTERADA — Atualizada em razão das alterações promovidas pela {ato_derivativo}"
            titulo = f"Versão Alterada - {ato_original}"
        else:
            tag = f"VERSÃO CONSOLIDADA — Atualizada em razão das revogações e/ou alterações promovidas pela {ato_derivativo}"
            titulo = f"Versão Consolidada - {ato_original}"

        html_final = MODELO_HTML_ESTRITO.format(
            titulo_documento=titulo,
            tag_versao=tag,
            link_original=link_original,
            nome_original=ato_original,
            link_derivativo=link_derivativo,
            nome_derivativo=ato_derivativo,
            corpo_texto=corpo_construido
        )
        
        return Response(
            html_final,
            mimetype="text/html",
            headers={{"Content-disposition": f"attachment; filename={{tipo_versao}}_consolidada.html"}}
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
