#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser Itaú – com stoplist de Compras Parceladas (CP) capturada na Passada 2.
"""

import re
import pdfplumber
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, List, Pattern, Set
import unicodedata

# --- Regex principais ---
RX_TRANSACAO = re.compile(r"(\d{2}/\d{2})\s+(.+?)\s+([−-]?\s?\d{1,3}(?:\.\d{3})*,\d{2})")
RX_CARTAO_HEADER_1 = re.compile(r"^Lançamentos no cartão\s*\(final\s*(\d{4})\)", re.I)
RX_CARTAO_HEADER_2 = re.compile(r"\(final\s*(\d{4})\)", re.I)

# Blocos a remover/ignorar (passada 1 - texto por linhas)
RX_INICIO_CP = re.compile(r"^\s*Compras\s+parceladas\s*-\s*pr[oó]ximas\s+faturas\s*$", re.I)
RX_FIM_CP = [
    re.compile(r"^\s*Total\s+para\s+próximas\s+faturas\s*$", re.I),
    re.compile(r"^\s*Lançamentos\s+no\s+cartão\s*\(final\s+\d{4}\)\s*$", re.I),
    re.compile(r"^\s*Lançamentos:\s*compras\s+e\s+saques\s*$", re.I),
    re.compile(r"^\s*Limites\s+de\s+crédito", re.I),
]
RX_FIQUE_ATENTO_INICIO = re.compile(r"Fique\s+atento\s+aos\s+encargos\s+para\s+o\s+pr[oó]ximo\s+per[ií]odo", re.I)

# Versões "inline" (passada 2 - texto achatado)
RX_INICIO_CP_INLINE = re.compile(r"Compras\s+parceladas\s*-\s*pr[oó]ximas\s+faturas", re.I)
RX_FIM_CP_INLINE = [
    re.compile(r"Total\s+para\s+próximas\s+faturas", re.I),
    re.compile(r"Lançamentos\s+no\s+cartão\s*\(final\s+\d{4}\)", re.I),
    re.compile(r"Lançamentos:\s*compras\s+e\s+saques", re.I),
    re.compile(r"Limites\s+de\s+crédito", re.I),
]

# Título inline (coluna direita costuma vir "achatada")
RX_FIQUE_ATENTO_INLINE = re.compile(
    r"Fique\s*atento\s*aos?\s*encargos\s*para\s*o\s*pr[oó]xim[oa]\s*per[ií]odo\s*\(\s*\d{2}/\d{2}\s*a\s*\d{2}/\d{2}\s*\)",
    re.I
)
RX_FIM_FIQUE_INLINE = [
    re.compile(r"Juros\s+M[aá]ximos\s+do\s+contrato", re.I),
    re.compile(r"Novo\s+teto\s+de\s+juros.*cart[aã]o", re.I),
    re.compile(r"Cr[eé]dito\s+Rotativo\s*/\s*Atraso", re.I),
    re.compile(r"Os\s+juros\s+e\s+encargos.*ser[aã]o\s+devolvidos", re.I),
] + RX_FIM_CP_INLINE

# Internacionais (bloco)
RX_INT_TITULO = re.compile(r"^\s*Lançamentos\s+internacionais\s*$", re.I)

# aceita "Repasse de IOF em R$ 4,07", "Repasse do IOF R$4,07", etc.
RX_INT_IOF = re.compile(
    r"Repasse\s+d[eo]?\s*IOF\s+(?:em\s+)?R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})",
    re.I
)
RX_TOTAL_TRANS_INTER = re.compile(
    r"Total\s+transa[cç][õo]es\s+inter\.\s+em\s+R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})",
    re.I
)
RX_TOTAL_LANC_INTER = re.compile(
    r"Total\s+lan[cç]amentos\s+inter\.\s+em\s+R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})",
    re.I
)
RX_DATA_VENCIMENTO = re.compile(
    r"Vencimento:\s(\d{2}/\d{2}/\d{4})",
    re.I
)

RX_INT_IGNORAR = [
    re.compile(r"\bUSD\b", re.I),
    re.compile(r"D[óo]lar\s+de\s+Convers[aã]o", re.I),
    re.compile(r"^Total\s+transa[cç][õo]es\s+inter\.\s+em\s+R\$", re.I),
    re.compile(r"^Total\s+lan[cç]amentos\s+inter\.\s+em\s+R\$", re.I),
]

IOF_SEM_CARTAO = "__SEM_CARTAO__"

# Rabicho típico
RX_FIQUE_RABICHO = re.compile(r"^a\s*\d{2}/\d{2}\)?$", re.I)

# ---------------- helpers ----------------
def valor_para_float(valor: str) -> float:
    v = valor.replace(" ", "").replace("−", "-")
    return float(v.replace(".", "").replace(",", "."))

def float_para_brl_str(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def remover_bloco_por_marcas(texto: str, inicio_regex: Pattern, fins_regex_list: List[Pattern]) -> str:
    while True:
        m_ini = inicio_regex.search(texto)
        if not m_ini:
            break
        start = m_ini.start()
        seg = texto[start:]
        fim_pos: Optional[int] = None
        for rx in fins_regex_list:
            m = rx.search(seg)
            if m:
                cand = start + m.start()
                fim_pos = cand if fim_pos is None else min(fim_pos, cand)
        if fim_pos is None:
            texto = texto[:start]
        else:
            texto = texto[:start] + texto[fim_pos:]
    return texto

def extrair_blocos_por_marcas(texto: str, inicio_regex: Pattern, fins_regex_list: List[Pattern]) -> List[str]:
    """Retorna o(s) conteúdo(s) entre INICIO e o 1º FIM encontrado, repetidamente."""
    blocos: List[str] = []
    cursor = 0
    while True:
        m_ini = inicio_regex.search(texto, cursor)
        if not m_ini:
            break
        start = m_ini.end()
        seg = texto[start:]
        fim_pos: Optional[int] = None
        for rx in fins_regex_list:
            m = rx.search(seg)
            if m:
                cand = start + m.start()
                if fim_pos is None or cand < fim_pos:
                    fim_pos = cand
        if fim_pos is None:
            bloco = texto[start:]
            blocos.append(bloco)
            break
        else:
            bloco = texto[start:fim_pos]
            blocos.append(bloco)
            cursor = fim_pos
    return blocos

def remover_bloco_cp(texto: str) -> str:
    return remover_bloco_por_marcas(texto, RX_INICIO_CP, RX_FIM_CP)

def remover_bloco_cp_inline(texto: str) -> str:
    return remover_bloco_por_marcas(texto, RX_INICIO_CP_INLINE, RX_FIM_CP_INLINE)

def remover_bloco_fique(texto: str) -> str:
    return remover_bloco_por_marcas(texto, RX_FIQUE_ATENTO_INICIO, RX_FIM_CP)

def remover_bloco_fique_inline(texto: str) -> str:
    return remover_bloco_por_marcas(texto, RX_FIQUE_ATENTO_INLINE, RX_FIM_FIQUE_INLINE)

def remover_bloco_internacionais(texto: str) -> str:
    return remover_bloco_por_marcas(texto, RX_INT_TITULO, RX_FIM_CP)

def detectar_cartao(linha: str, cartao_atual: Optional[str]) -> Optional[str]:
    m1 = RX_CARTAO_HEADER_1.search(linha)
    if m1:
        return m1.group(1)
    m2 = RX_CARTAO_HEADER_2.search(linha)
    if m2:
        return m2.group(1)
    return cartao_atual

def _norma(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()

def make_key(data: str, estab: str, valor_str: str) -> str:
    v = round(valor_para_float(str(valor_str)), 2)
    return f"{data.strip()}|{_norma(estab)}|{v:.2f}"

def predict_date(data_item:str, data_fatura: Optional[date]):
    if not data_fatura:
        raise ValueError("Data de fatura não pode ser None")
    
    item_data = datetime.strptime(data_item, '%d/%m').date()

    if item_data.month < data_fatura.month or (item_data.month == data_fatura.month and item_data.day < data_fatura.day):
        item_data = item_data.replace(year=data_fatura.year)
    else:
        item_data = item_data.replace(year=data_fatura.year - 1)
    
    return item_data.strftime('%d/%m/%Y')

# ---------------- parser ----------------
def processar_pdf(caminho_pdf: str) -> pd.DataFrame:
    DATA_EXPORTACAO = date.today().strftime("%d/%m/%Y")
    DATA_VENCIMENTO = None
    dados: List[Dict] = []
    iof_por_cartao: Dict[str, float] = {}
    cp_keys: Set[str] = set()  # stoplist de CP

    # =======================
    # PASSADA 1 (por linhas)
    # =======================
    with pdfplumber.open(caminho_pdf) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = remover_bloco_cp(text)
            text = remover_bloco_fique(text)
    
            linhas = text.split("\n")
            cartao: Optional[str] = None
            em_internacionais = False
    
            for ln in linhas:
                has_data_vencimento = RX_DATA_VENCIMENTO.search(ln)
                if not DATA_VENCIMENTO and has_data_vencimento:
                    DATA_VENCIMENTO = datetime.strptime(has_data_vencimento.group(1), '%d/%m/%Y').date()

                cartao = detectar_cartao(ln, cartao)
    
                if RX_INT_TITULO.search(ln):
                    em_internacionais = True
                    if cartao and cartao not in iof_por_cartao:
                        iof_por_cartao[cartao] = 0.0
                    if IOF_SEM_CARTAO not in iof_por_cartao:
                        iof_por_cartao[IOF_SEM_CARTAO] = 0.0
                    continue
    
                if em_internacionais:
                    if any(rx.search(ln) for rx in RX_FIM_CP) or RX_CARTAO_HEADER_1.search(ln):
                        em_internacionais = False
                        continue
    
                    m_iof = RX_INT_IOF.search(ln)
                    if m_iof:
                        val_iof = valor_para_float(m_iof.group(1))
                        chave = cartao if cartao else IOF_SEM_CARTAO
                        iof_por_cartao[chave] = iof_por_cartao.get(chave, 0.0) + val_iof
                        continue
    
                    if any(rx.search(ln) for rx in RX_INT_IGNORAR):
                        continue
    
                    mtx = RX_TRANSACAO.match(ln)
                    if mtx:
                        data, estabelecimento, valor = mtx.groups()
                        data = predict_date(data, DATA_VENCIMENTO)
                        dados.append({
                            "Data": data,
                            "Estabelecimento": estabelecimento.strip(),
                            "Valor (R$)": float_para_brl_str(valor_para_float(valor)),
                            "Passada": 1,
                            "Pagina": page_idx,
                            "Coluna": 1,
                        })
                    continue
    
                m = RX_TRANSACAO.match(ln)
                if m:
                    data, estabelecimento, valor = m.groups()
                    data = predict_date(data, DATA_VENCIMENTO)
                    dados.append({
                        "Data": data,
                        "Estabelecimento": estabelecimento.strip(),
                        "Valor (R$)": float_para_brl_str(valor_para_float(valor)),
                        "Passada": 1,
                        "Pagina": page_idx,
                        "Coluna": 1,
                    })


    # IOF por cartão (passada 1)
    for cartao, iof_val in iof_por_cartao.items():
        if not iof_val:
            continue
        if cartao == IOF_SEM_CARTAO:
            desc = "Repasse de IOF (transações internacionais)"
        else:
            desc = f"Repasse de IOF (transações internacionais) – final {cartao}"
        dados.append({
            "Data": DATA_EXPORTACAO,
            "Estabelecimento": desc,
            "Valor (R$)": float_para_brl_str(iof_val),
            "Passada": 1,
        })

    # =======================
    # PASSADA 2 (coluna 2 achatada)
    # =======================
    with pdfplumber.open(caminho_pdf) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            palavras = page.extract_words() or []
            meio = page.width / 2
            coluna_2 = [p for p in palavras if p["x0"] >= meio]
    
            texto_c2 = " ".join(p["text"] for p in coluna_2)
    
            # Remove "Fique atento" bruto
            texto_c2 = re.sub(
                r"Fique\s*atento.*?\(\s*\d{2}/\d{2}\s*a\s*\d{2}/\d{2}\s*\)\s*",
                " ",
                texto_c2,
                flags=re.I | re.S,
            )
    
            # --- CAPTURA CP PRA STOPLIST (antes de remover CP) ---
            blocos_cp = extrair_blocos_por_marcas(texto_c2, RX_INICIO_CP_INLINE, RX_FIM_CP_INLINE)
            for bloco in blocos_cp:
                for m in RX_TRANSACAO.finditer(bloco):
                    data, estabelecimento, valor = m.groups()
                    cp_keys.add(make_key(data, estabelecimento, valor))
    
            # Limpezas usuais
            texto_c2 = remover_bloco_fique_inline(texto_c2)
            texto_c2 = remover_bloco_cp_inline(texto_c2)
            texto_c2 = remover_bloco_fique(texto_c2)
    
            # tenta inferir o "final do cartão" na direita
            cartao_c2 = None
            m_card = RX_CARTAO_HEADER_2.search(texto_c2)
            if m_card:
                cartao_c2 = m_card.group(1)
    
            valor_iof_dir = None
            m_iof_dir = RX_INT_IOF.search(texto_c2)
            if m_iof_dir:
                valor_iof_dir = valor_para_float(m_iof_dir.group(1))
            else:
                m_tot = RX_TOTAL_TRANS_INTER.search(texto_c2)
                m_lan = RX_TOTAL_LANC_INTER.search(texto_c2)
                if m_tot and m_lan:
                    v_tot = valor_para_float(m_tot.group(1))
                    v_lan = valor_para_float(m_lan.group(1))
                    diff = round(v_lan - v_tot, 2)
                    if 0 <= diff <= 50:
                        valor_iof_dir = diff
    
            if valor_iof_dir is not None:
                chave = cartao_c2 or IOF_SEM_CARTAO
                if iof_por_cartao.get(chave, 0.0) == 0.0:
                    iof_por_cartao[chave] = valor_iof_dir
    
            texto_c2 = remover_bloco_internacionais(texto_c2)
    
            for m in RX_TRANSACAO.finditer(texto_c2):
                data, estabelecimento, valor = m.groups()
                estabelecimento = estabelecimento.strip()
                if RX_FIQUE_RABICHO.match(estabelecimento):
                    continue
                data = predict_date(data, DATA_VENCIMENTO)
                dados.append({
                    "Data": data,
                    "Estabelecimento": estabelecimento,
                    "Valor (R$)": float_para_brl_str(valor_para_float(valor)),
                    "Passada": 2,
                    "Pagina": page_idx,
                    "Coluna": 2,
                })
        # =======================
        # PASSADA 3 – Fallback robusto de IOF (por página, texto bruto)
        # =======================
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                cartao_local = None
        
                # 3.1) Tenta capturar pelo "Repasse de IOF ..." linha a linha
                for ln in txt.split("\n"):
                    # acompanha o "final ####" da página
                    m_card = RX_CARTAO_HEADER_1.search(ln) or RX_CARTAO_HEADER_2.search(ln)
                    if m_card:
                        cartao_local = m_card.group(1)
        
                    m_iof = RX_INT_IOF.search(ln)
                    if m_iof:
                        chave = cartao_local or IOF_SEM_CARTAO
                        if iof_por_cartao.get(chave, 0.0) == 0.0:
                            iof_por_cartao[chave] = valor_para_float(m_iof.group(1))
        
                # 3.2) Se ainda não pegou IOF nessa página, tenta diferença de totais
                #     (usa o mesmo cartao_local, se houver)
                chave_fallback = cartao_local or IOF_SEM_CARTAO
                if iof_por_cartao.get(chave_fallback, 0.0) == 0.0:
                    m_tot = RX_TOTAL_TRANS_INTER.search(txt)
                    m_lan = RX_TOTAL_LANC_INTER.search(txt)
                    if m_tot and m_lan:
                        v_tot = valor_para_float(m_tot.group(1))
                        v_lan = valor_para_float(m_lan.group(1))
                        diff = round(v_lan - v_tot, 2)
                        if 0 <= diff <= 50:
                            iof_por_cartao[chave_fallback] = diff


        # =======================
        # DEDUPE DE IOF (preferir específico ao genérico)
        # =======================
        def _dedupe_iof(iof_dict: Dict[str, float]) -> Dict[str, float]:
            # normaliza/arrenda
            for k in list(iof_dict.keys()):
                try:
                    iof_dict[k] = round(float(iof_dict[k]), 2)
                except Exception:
                    iof_dict[k] = 0.0
        
            if IOF_SEM_CARTAO in iof_dict:
                gen = iof_dict[IOF_SEM_CARTAO]
                specs = {k: v for k, v in iof_dict.items() if k != IOF_SEM_CARTAO and v > 0}
        
                if specs:
                    # Remove o genérico se:
                    # 1) houver valor específico igual a ele (dentro da tolerância), ou
                    # 2) a soma dos específicos “bate” com o genérico (alguns layout somam por cartão)
                    soma_specs = round(sum(specs.values()), 2)
                    match_algum = any(abs(gen - v) <= 0.01 for v in specs.values())
                    match_soma  = abs(gen - soma_specs) <= 0.01
        
                    if match_algum or match_soma or gen <= 0.01:
                        iof_dict.pop(IOF_SEM_CARTAO, None)
        
            return iof_dict
        
        # Aplique a dedupe ANTES de materializar as linhas de IOF:
        iof_por_cartao = _dedupe_iof(iof_por_cartao)
        
        # =======================
        # MATERIALIZA IOF (sem duplicar)
        # =======================
        iof_rows_seen = set()
        for cartao, iof_val in iof_por_cartao.items():
            if not iof_val or iof_val <= 0:
                continue
            if cartao == IOF_SEM_CARTAO:
                desc = "Repasse de IOF (transações internacionais)"
            else:
                desc = f"Repasse de IOF (transações internacionais) – final {cartao}"
        
            key = (desc, round(iof_val, 2))
            if key in iof_rows_seen:
                continue  # evita duplicar mesma linha
            iof_rows_seen.add(key)
        
            dados.append({
                "Data": DATA_EXPORTACAO,
                "Estabelecimento": desc,
                "Valor (R$)": float_para_brl_str(iof_val),
                "Passada": 1,
                "Pagina": None, "Coluna": None, "Bloco": "INTERNACIONAL",
            })



    # =======================
    # DF final
    # =======================
    df = pd.DataFrame(
        dados,
        columns=["Data", "Estabelecimento", "Valor (R$)", "Passada", "Pagina", "Coluna"]
    )

    est_norm = df["Estabelecimento"].astype(str).map(_norma)
    mask_pag = est_norm.str.startswith("pagamento") | est_norm.str.contains(r"\bpagamentos?\b|\bpagto\b")
    df = df[~mask_pag].copy()

    # Normalização de valores e deduplicação (prefere Passada 2)
    df["_valor_num"] = df["Valor (R$)"].apply(lambda s: valor_para_float(str(s)))
    df["Valor (R$)"] = df["_valor_num"].apply(lambda v: float_para_brl_str(round(v, 2)))

    def _norm_est(s: str) -> str:
        return re.sub(r"\s+", " ", str(s)).strip()

    df["_key"] = (
        df["Data"].astype(str).str.strip()
        + "|" + df["Estabelecimento"].map(_norm_est).map(_norma)
        + "|" + df["_valor_num"].round(2).map(lambda v: f"{v:.2f}")
    )

    # aplica stoplist de CP
    if cp_keys:
        df = df[~df["_key"].isin(cp_keys)].copy()

    df = df.sort_values(["Data", "Estabelecimento", "_valor_num", "Passada"])
    df = df.drop_duplicates(subset=["_key"], keep="last").reset_index(drop=True)
    df = df.drop(columns=["_key", "_valor_num"])

    return df
