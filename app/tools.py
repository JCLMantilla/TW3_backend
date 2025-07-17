import requests
import httpx
import os
import asyncio
import logging
from typing import List, Dict
from pydantic import BaseModel
from requests.exceptions import RequestException
import time
import json

import dotenv
dotenv.load_dotenv()

from app.utils import ScrapingBeeService, html_cleaner




# ULTIMATE SEARCH ENGINE


async def google_search_tool(query: str) -> str:

    '''
    Get information for the LLM, this will use a query toperform a google search and get the the raw html of the top n links. Then use redability package, beautiful soup and regex to clean the html and get the paragraphs suitable to be used in the LLM
    '''
    scraper = ScrapingBeeService()
    # Some parameters for the search engine
    n = 3 # Number of links to be visited by the search engine, we will use a small number of links to visit due to the limited number of credits we have on the free tier of ScrapingBee.
    top_k_paragraphs = 3 # Number of first big paragraphs found in the html to be used later. This affects the LLM's costs


    start = time.time()
    try:   
        # Do a google search with the query
        google_search_results = scraper.search(query)
        # Acess the raw contents of the first n links
        top_n_results = await scraper.access_top_n_links_async(results=google_search_results, n = n)

        # Clean the html and get the paragraphs suitable to be used in the LLM
        search_results = [{"source" : result.get('link', None),  
                           "contents" : html_cleaner(result.get('parsed_content', ''), top_k_paragraphs)  
                           } for result in top_n_results]
        # Dumps the results into a json string
        out = json.dumps(search_results)
        
    except Exception as e:
        logging.error(f"Error when getting information from ScrapingBee: {e}")
        return "No results found"
    
    end = time.time()
    logging.info(f" It took {end - start} seconds to do the internet search ")

    return out



# This is the base model for Qwen

# Import OpenAI library again (duplicate import)
# from openai import OpenAI

# Initialize OpenAI client with API key and base URL
# client = OpenAI(
#     # If environment variables are not configured, replace the following line with: api_key="sk-xxx",
#     api_key="secret api key", 
#     base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
# )

# Create a chat completion using the Qwen model
# completion = client.chat.completions.create(
#     model="qwen2.5-32b-instruct",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "Who are you?"}],
#     )
    
# Print the completion response as JSON (commented out)
#print(completion.model_dump_json())

# Get the content of the first message choice
# completion.choices[0].message.content



