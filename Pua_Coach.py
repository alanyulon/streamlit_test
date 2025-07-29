import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

# CONFIGURAÇÃO INICIAL
st.set_page_config(layout="wide", page_title="PUA Coach")
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# FUNÇÕES DE CACHE (evita recomputar recursos pesados)
@st.cache_resource
def criar_vector_store_e_assistant():
    vector_store_id = os.getenv('vector_store_id')
    assistant_id = os.getenv('assistant_id')
    return vector_store_id, assistant_id

@st.cache_resource
def criar_thread():
    return client.beta.threads.create()

def enviar_pergunta(thread, user_input):
    return client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=user_input
    )

def obter_resposta_assistente(thread, assistant_id):
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions='O nome do usuário é A, e ela é um usuário Premium.'
    )
    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    if run.status != 'completed':
        return f'Erro na execução: {run.status}'

    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    mensagem = list(mensagens)[0].content[0].text
    anotacoes = mensagem.annotations
    citacoes = []

    for idx, anotacao in enumerate(anotacoes):
        mensagem.value = mensagem.value.replace(anotacao.text, f"[{idx}]")
        if file_cit := getattr(anotacao, 'file_citation', None):
            file = client.files.retrieve(file_cit.file_id)
            citacoes.append(f"[{idx}] {file.filename}")

    if citacoes:
        mensagem.value += "\n\n" + "\n".join(citacoes)

    return mensagem.value

# MAIN FUNCTION
def main():
    st.title("Mistery Coach")

    # Inicializações com cache
    vector_store, assistant_id = criar_vector_store_e_assistant()
    thread = criar_thread()

    # Inicializar estado da conversa
    if 'mensagens' not in st.session_state:
        st.session_state.mensagens = []

    # Exibe histórico
    for entrada in st.session_state.mensagens:
        with st.chat_message(entrada["role"]):
            st.markdown(entrada["mensagem"])

    # Campo de entrada do usuário
    user_input = st.chat_input("Fale algo...")

    if user_input:
        # Mostra a mensagem do usuário
        st.session_state.mensagens.append({"role": "user", "mensagem": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Obtém resposta do assistente
        enviar_pergunta(thread, user_input)
        resposta = obter_resposta_assistente(thread, assistant_id)

        # Mostra resposta
        st.session_state.mensagens.append({"role": "assistant", "mensagem": resposta})
        with st.chat_message("assistant"):
            st.markdown(resposta)

# Execução
if __name__ == '__main__':
    main()