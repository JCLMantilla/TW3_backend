import os
import logging
import requests

from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel

import dotenv
dotenv.load_dotenv()

from langchain_core.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI

from app.tools import google_search_tool

# Define our search tool for the agent
search_tool = Tool(
    name="SearchTool",
    func=google_search_tool,            # your async function
    coroutine=google_search_tool,       # MUST set this for async support
    description="Use this tool to retrieve factual information with their sources. This is useful to answer factual or knowledge-based questions"
)

# Set our Qwen model as a ChatOpenAI-like model
llm = ChatOpenAI(
    openai_api_key=os.getenv("QWEN_API_KEY"),
    openai_api_base="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    model_name="qwen2.5-32b-instruct",
    temperature=0.7
)

# Define our memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Agent init
agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)


# Lifespan events on the app if needed
@asynccontextmanager
async def lifespan(app: FastAPI):
    # We have to define a global variable where we are going to store the data to yield
    global startup_data
    startup_data = {}
    # Start app
    variable = 0
    startup_data["dummy_variable"] = variable

    yield
    # End app
    del startup_data




# APP 
app = FastAPI(lifespan=lifespan)

# Define request body format
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        response = agent.run(req.message)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    return {"Hello": "The backend is running"}



