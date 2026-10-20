"""Componentes de geração e download de relatórios."""

import hashlib
from pathlib import Path

import streamlit as st

from .exportacao_pdf import render_pdf


def pdf_actions(title, filename, sections, key):
    signature = hashlib.sha256(repr((title, filename, sections)).encode("utf-8")).hexdigest()
    saved = st.session_state.get("pdf_" + key)
    if st.button("Transformar em PDF", key="make_pdf_" + key):
        try:
            with st.spinner("Preparando o PDF…"):
                saved = (signature, render_pdf(title, filename, sections))
                st.session_state["pdf_" + key] = saved
        except ImportError:
            st.error("Instale as dependências atualizadas do projeto para gerar o PDF.")
        except Exception:
            st.error("Não foi possível montar o PDF. Tente novamente com um resultado menor.")
    if saved and saved[0] == signature:
        st.download_button("Baixar PDF", saved[1], file_name=f"{key}_{Path(filename).stem}.pdf",
                           mime="application/pdf", key="download_pdf_" + key)
