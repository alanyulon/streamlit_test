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
    # caminho_pasta_book = Path(r"C:\Users\alany\Documents\_Sources\PUA\Books")
    # caminho_pasta_transcriptions = Path(r"C:\Users\alany\Documents\_Sources\PUA\Transcriptions")
    # files = [open(f, 'rb') for f in caminho_pasta_book.glob('*.pdf')] + [open(f, 'rb') for f in caminho_pasta_transcriptions.glob('*.pdf')]
    vector_store_id = 'vs_68875d895b688191a94050b8fa0c081f'
    assistant_id = 'asst_IGhIG2TjTC0vXImdAvJ5amhn'

    # vector_store = client.vector_stores.create(name='PUA_Sources')
    # client.vector_stores.file_batches.upload_and_poll(
    #     vector_store_id=vector_store_id,
    #     files=files
    # )
    # assistant = client.beta.assistants.create(
    #     name='Mistery',
    #     instructions=(
    #         "Você é um instrutor de artes de sedução. Responda apenas com base nesse tema,\
    #          utilizando as apostilas fornecidas. Seja criativo e objetivo."
    #     ),
    #     tools=[{'type': 'file_search'}],
    #     tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}},
    #     model='gpt-4o'
    # )
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
    st.title("PUA Coach")

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