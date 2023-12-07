from langchain.chains.llm import LLMChain
from langchain.document_loaders import Docx2txtLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import TextLoader

import os
from langchain.llms import AzureOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

# os.environ["OPENAI_API_TYPE"] = "azure"
# os.environ["OPENAI_API_BASE"] = "https://utterancesresource.openai.azure.com/"
# os.environ["OPENAI_API_KEY"] = "5ea3e8e59b8a418e9cc3c066f853b0c0"
# os.environ["OPENAI_API_VERSION"] = "2023-07-01-preview"

os.environ["OPENAI_API_KEY"]= 'e63ed695495543d58595fab4e27e4ff1'
os.environ['OPENAI_API_VERSION'] = '2023-07-01-preview'
os.environ['OPENAI_API_BASE'] = 'https://tv-llm-applications.openai.azure.com/'
os.environ['OPENAI_API_TYPE'] = 'azure'

def pdf_query_updated(query, text_splitter, llm, query_options, memory):  

    documents_query = []
    for file in query_options:
        if file.endswith('.pdf'):
            pdf_path = './documents/' + file
            loader = PyPDFLoader(pdf_path)
            documents_query.extend(loader.load())
        elif file.endswith('.docx') or file.endswith('.doc'):
            doc_path = './documents/' + file
            # print(doc_path,'*'*117)
            loader = Docx2txtLoader(doc_path)
            documents_query.extend(loader.load())
        elif file.endswith('.txt'):
            text_path = './documents/' + file
            loader = TextLoader(text_path)
            documents_query.extend(loader.load())


    docs=text_splitter.split_documents(documents_query)
    # embeddings=HuggingFaceEmbeddings(model_name = 'sentence-transformers/all-MiniLM-L6-v2')
    embeddings = OpenAIEmbeddings(deployment='ada-embed',
                                  openai_api_key='e63ed695495543d58595fab4e27e4ff1',
                                  openai_api_base= 'https://tv-llm-applications.openai.azure.com/',
                                  openai_api_type="azure",
                                  openai_api_version='2023-07-01-preview',
                                  chunk_size=16)
    
    document_search = FAISS.from_texts([t.page_content for t in docs], embeddings)


    template = """You are an AI having a conversation with a human.

    Given the following extracted parts of a long document and a question, create a final answer.
    And if you can't find the answer, strictly mention "Currently I am unable to answer this questions based on my knowledge. Please reach out to us - support@guardsman.com"

    {context}

    {chat_history}
    Human: {human_input}
    AI:"""

    prompt = PromptTemplate(input_variables=["chat_history", "human_input", "context"], template=template)
    chain = LLMChain(llm = llm, prompt = prompt,memory = memory)

    result, context_docs = llm_query(query, document_search, chain)

    return result, context_docs


def llm_query(query, document_search, chain):
    
    docs = document_search.similarity_search(query)
    chain_res = chain.predict(human_input = query, context = docs).split('Human:')[0]
    return chain_res + '\n\n', docs


# file_path = r"QandA.docx"
# memory = ConversationBufferMemory()
# query_options = [file_path]
# human_query = 'what leave policies do I have'
# text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# llm = AzureOpenAI(deployment_name='gpt-0301', temperature = 0)
# memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')

# response, context_docs = pdf_query_updated(query = human_query, text_splitter = text_splitter, llm = llm, query_options = query_options, memory = memory)