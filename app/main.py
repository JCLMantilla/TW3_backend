import os
import logging
import requests
import asyncio
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

import dotenv
dotenv.load_dotenv()


# Allow your frontend origin
#origins = [
#    "http://localhost:3000",  # your frontend
#]

# Get frontend URL and port from environment variables, with fallbacks
frontend_url = os.getenv('FRONTEND_URL', 'localhost')
frontend_port = os.getenv('FRONTEND_PORT', '3000')

origins = [
    f"http://{frontend_url}:{frontend_port}",  # your frontend
    "http://localhost:3000",  # fallback for common frontend port
    "http://127.0.0.1:3000",  # alternative localhost format
]


from langchain_core.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.tools import google_search_tool


# Define our search tool for the agent
search_tool = Tool(
    name="SearchTool",
    coroutine=google_search_tool,    
    func=google_search_tool,       
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

# Create a prompt template for the agent
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that can search the internet for information. Always use the search tool when you need to find factual information."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent
agent = create_openai_tools_agent(llm, [search_tool], prompt)

# Create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=[search_tool], memory=memory, verbose=True)


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # can also use ["*"] for all origins (not recommended for prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request body format
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        response = await agent_executor.ainvoke({"input": req.message})
        return {"response": response["output"]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    return {"Hello": "The backend is running"}



