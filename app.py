#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug  9 15:58:40 2025

@author: jopenedo
"""

# app.py
# -*- coding: utf-8 -*-
import streamlit as st
from io import BytesIO
from pathlib import Path
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

from parser import processar_pdf  # <- sua função já pronta

# ===== Config / versão =====
APP_VERSION = "v1.0.0"  # altere aqui sempre que fizer mudanças

st.set_page_config(page_title="Conversor de Fatura Itaú → Planilha", page_icon="📄", layout="centered")

# Header com versão
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:12px;">
        <h1 style="margin:0;">Conversor de Fatura Itaú (PDF)→(CSV)</h1>
        <span style="background:#EEF2FF; color:#444; border:1px solid #CBD5E1; padding:2px 8px; border-radius:999px; font-size:12px;">
            {APP_VERSION}
        </span>
    </div>
    <div style="margin-top:6px; color:#666;">Selecione uma ou mais faturas em PDF. Eu converto para planilha (CSV).</div>
    """,
    unsafe_allow_html=True,
)

pdf_files = st.file_uploader("Importar PDFs das faturas", type=["pdf"], accept_multiple_files=True)

if pdf_files:
    st.info(f"{'Arquivo' if len(pdf_files) == 1 else 'Arquivos'} recebido{'s' if len(pdf_files) > 1 else ''}. Clique em **Processar PDFs** para iniciar.")
    
    # Opção para processar tudo junto ou separadamente
    col1, col2 = st.columns([1, 1])
    with col1:
        processar_junto = st.checkbox("Processar tudo em uma única planilha", value=True)
    with col2:
        mostrar_preview = st.checkbox("Mostrar preview dos dados", value=True)
    
    if st.button("Processar PDFs"):
        import tempfile
        import os
        
        all_dataframes = []
        file_results = {}
        
        # Processamento com barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, pdf_file in enumerate(pdf_files):
            status_text.text(f"Processando {pdf_file.name} ({i+1}/{len(pdf_files)})...")
            progress_bar.progress((i + 1) / len(pdf_files))
            
            with st.spinner(f"Processando {pdf_file.name}..."):
                # Salva o upload em arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.read())
                    tmp_path = tmp.name

                try:
                    # Processa o PDF
                    df = processar_pdf(tmp_path)
                    df['Arquivo_Origem'] = pdf_file.name  # Adiciona coluna com nome do arquivo
                    
                    all_dataframes.append(df)
                    file_results[pdf_file.name] = {
                        'df': df,
                        'success': True,
                        'error': None
                    }
                    
                except Exception as e:
                    file_results[pdf_file.name] = {
                        'df': None,
                        'success': False,
                        'error': str(e)
                    }
                    st.error(f"Erro ao processar {pdf_file.name}: {e}")
                
                # Limpa arquivo temporário
                os.unlink(tmp_path)
        
        progress_bar.empty()
        status_text.empty()
        
        # Resultados do processamento
        sucessos = sum(1 for result in file_results.values() if result['success'])
        erros = len(file_results) - sucessos
        
        if sucessos > 0:
            st.success(f"Processamento concluído! {sucessos} arquivo{'s' if sucessos != 1 else ''} processado{'s' if sucessos != 1 else ''} com sucesso.")
            
            if erros > 0:
                st.warning(f"{erros} arquivo{'s' if erros != 1 else ''} apresentou{'aram' if erros != 1 else ''} erro{'s' if erros != 1 else ''}.")
        else:
            st.error("Nenhum arquivo foi processado com sucesso.")
            st.stop()
        
        if processar_junto and all_dataframes:
            # Combina todos os DataFrames
            df_combined = pd.concat(all_dataframes, ignore_index=True)
            
            if mostrar_preview:
                st.subheader("📊 Preview dos dados combinados")
                st.dataframe(df_combined, use_container_width=True)
            
            # Estatísticas consolidadas
            try:
                total_valor = df_combined["Valor (R$)"].replace(",", ".", regex=True).astype(float).sum()
                st.markdown(f"**💰 Total geral dos lançamentos: R$ {total_valor:,.2f}**"
                           .replace(",", "X").replace(".", ",").replace("X", "."))
                
                # Estatísticas por arquivo
                st.subheader("� Estatísticas por arquivo")
                for arquivo in df_combined['Arquivo_Origem'].unique():
                    df_arquivo = df_combined[df_combined['Arquivo_Origem'] == arquivo]
                    total_arquivo = df_arquivo["Valor (R$)"].replace(",", ".", regex=True).astype(float).sum()
                    st.write(f"• **{arquivo}**: {len(df_arquivo)} lançamentos, Total: R$ {total_arquivo:,.2f}"
                            .replace(",", "X").replace(".", ",").replace("X", "."))
                    
            except Exception as e:
                st.warning(f"Não foi possível calcular os totais: {e}")

            # Download da planilha combinada
            base_name = f"Faturas_Itau_Combinadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            buffer = BytesIO()
            buffer.write(df_combined.to_csv(index=False).encode("utf-8-sig"))
            buffer.seek(0)
            
            st.download_button(
                label="📥 Baixar planilha combinada (CSV)",
                data=buffer,
                file_name=base_name,
                mime="text/csv",
            )

            # Botão copiar para área de transferência
            tsv = df_combined.to_csv(index=False, sep="\t")
            components.html(
                f"""
                <div>
                  <button id="copy-btn" style="
                      margin-top:10px;
                      padding:8px 12px;
                      border-radius:8px;
                      border:1px solid #cbd5e1;
                      background:#f8fafc;
                      cursor:pointer;">
                     📎 Copiar tabela combinada
                  </button>
                  <span id="copy-msg" style="margin-left:8px; color:#16a34a;"></span>
                  <textarea id="tsv-data" style="position:absolute; left:-10000px; top:-10000px;">{tsv}</textarea>
                </div>
                <script>
                  const btn = document.getElementById("copy-btn");
                  const msg = document.getElementById("copy-msg");
                  const data = document.getElementById("tsv-data").value;
                  btn.addEventListener("click", async () => {{
                    try {{
                      await navigator.clipboard.writeText(data);
                      msg.textContent = "Copiado!";
                      setTimeout(() => msg.textContent = "", 2000);
                    }} catch (e) {{
                      msg.style.color = "#dc2626";
                      msg.textContent = "Falha ao copiar";
                      setTimeout(() => msg.textContent = "", 3000);
                    }}
                  }});
                </script>
                """,
                height=60,
            )
        else:
            # Processamento individual - mostra cada arquivo separadamente
            st.subheader("📊 Resultados por arquivo")
            
            for pdf_file in pdf_files:
                result = file_results[pdf_file.name]
                
                if result['success']:
                    df = result['df']
                    st.write(f"### 📄 {pdf_file.name}")
                    
                    if mostrar_preview:
                        st.dataframe(df, use_container_width=True)
                    
                    try:
                        total_valor = df["Valor (R$)"].replace(",", ".", regex=True).astype(float).sum()
                        st.markdown(f"**💰 Total: R$ {total_valor:,.2f}** ({len(df)} lançamentos)"
                                   .replace(",", "X").replace(".", ",").replace("X", "."))
                    except Exception as e:
                        st.warning(f"Não foi possível calcular o total: {e}")

                    # Download individual
                    base_name = Path(pdf_file.name).stem + ".csv"
                    
                    buffer = BytesIO()
                    # Remove a coluna Arquivo_Origem para downloads individuais
                    df_download = df.drop(columns=['Arquivo_Origem']) if 'Arquivo_Origem' in df.columns else df
                    buffer.write(df_download.to_csv(index=False).encode("utf-8-sig"))
                    buffer.seek(0)
                    
                    st.download_button(
                        label=f"📥 Baixar {base_name}",
                        data=buffer,
                        file_name=base_name,
                        mime="text/csv",
                        key=f"download_{pdf_file.name}"
                    )
                else:
                    st.error(f"❌ {pdf_file.name}: {result['error']}")

        st.caption("💡 Dica: após baixar, abra o arquivo CSV no Excel ou LibreOffice Calc.")

