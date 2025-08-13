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
    <div style="margin-top:6px; color:#666;">Selecione sua fatura em PDF. Eu converto para planilha (CSV).</div>
    """,
    unsafe_allow_html=True,
)

pdf_file = st.file_uploader("Importar PDF da fatura", type=["pdf"])

if pdf_file is not None:
    st.info("Arquivo recebido. Clique em **Processar PDF** para iniciar.")
    if st.button("Processar PDF"):
        with st.spinner("Processando..."):
            # Salva o upload em memória temporária (Streamlit já fornece o buffer)
            # Para o parser, precisamos escrever em disco ou passar um caminho temporário.
            # Aqui usamos NamedTemporaryFile para caminho real.
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                tmp_path = tmp.name

            # Processa
            df = processar_pdf(tmp_path)

            # Preview
            st.success(f"Processado! {len(df)} linhas extraídas.")
            st.dataframe(df, use_container_width=True)
            
            try:
                total_valor = df["Valor (R$)"].replace(",", ".", regex=True).astype(float).sum()
                st.markdown(
                f"**💰 Total dos lançamentos: R$ {total_valor:,.2f}**"
                .replace(",", "X").replace(".", ",").replace("X", ".")
                )
            except Exception as e:
                st.warning(f"Não foi possível calcular o total: {e}")

            # ===== Nome do arquivo de saída: mesmo do PDF, extensão .csv =====
            # Ex.: "Fatura_Itau_20250807-153014.pdf" -> "Fatura_Itau_20250807-153014.csv"
            base_name = Path(pdf_file.name).stem + ".csv"

            # Gera CSV em memória
            buffer = BytesIO()
            buffer.write(df.to_csv(index=False).encode("utf-8-sig"))
            buffer.seek(0)
            
            st.download_button(
                label="Baixar planilha (CSV)",
                data=buffer,
                file_name=str(Path(base_name).with_suffix(".csv")),
                mime="text/csv",
            )

            # ===== Botão: Copiar tabela para a área de transferência =====
            # Dica: TSV (tab-separated) cola super bem no Excel mantendo vírgulas decimais.
            tsv = df.to_csv(index=False, sep="\t")
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
                     📎 Copiar tabela
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

            st.caption("Dica: após copiar, abra o Excel e cole (Ctrl/Cmd+V).")

