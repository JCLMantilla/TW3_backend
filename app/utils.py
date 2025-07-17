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


# This class is used to perform a google search with the scrapingbee API and also get the raw html of a website in order to access the contents that will be further cleaned and passed into the LLM.
class ScrapingBeeService:

    def __init__(self):

        self.BASE_URL = "https://app.scrapingbee.com/api/v1/"
        self.GOOGLE_SEARCH_ENDPOINT = f"{self.BASE_URL}store/google"
        self.API_KEY = os.environ.get("SCRAPINGBEE_API_KEY")  # Replace with your API key

    def search(self, query: str) -> dict:
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "api_key": self.API_KEY,
            "search": query,
            "language": "fr",
        }

        # Retry logic using requests
        try:
            response = requests.get(self.GOOGLE_SEARCH_ENDPOINT, headers=headers, params=params, timeout=20)
            response.raise_for_status()  # Raise exception for HTTP errors

            # Parse JSON response
            response_json = response.json()

            # Match ScrapingAPI format
            for result in response_json.get("organic_results", []):
                # Map 'url' to 'link'
                result["link"] = result.pop("url", None)

                # Rename 'displayed_url' to 'displayed_link'
                if "displayed_url" in result:
                    result["displayed_link"] = result.pop("displayed_url")

                # Rename 'description' to 'snippet'
                if "description" in result:
                    result["snippet"] = result.pop("description")

                # Keep 'date' if it exists
                if "date" in result:
                    result["date"] = result["date"]

                # Ensure 'sitelinks' exists as an empty list
                result.setdefault("sitelinks", [])

            return response_json

        except RequestException as e:
            logging.error(f"Failed to fetch data from ScrapingBee: {str(e)}")
            raise Exception(f"Failed to fetch data from ScrapingBee: {str(e)}")

    def access_url(self, url: str, render: bool = False) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "api_key": self.API_KEY,
            "url": url,
            "render_js": "true" if render else "false",
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            
            if response.status_code == 404:
                return "404"
            if response.status_code == 200:
                return response.text

            # Log errors for other response statuses
            logging.error(f"Failed to fetch data from ScrapingBee: {response.status_code} - {response.text} on URL: {url}")
            return "Could not load page"

        except RequestException as e:
            logging.error(f"Error while accessing URL: {url}. Exception: {str(e)}")
            return "Could not load page"

    async def access_url_async(self, url: str, render: bool = False) -> str:
        """
        Async version of access_url using httpx for concurrent requests
        """
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "api_key": self.API_KEY,
            "url": url,
            "render_js": "true" if render else "false",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, headers=headers, params=params)
                
                if response.status_code == 404:
                    return "404"
                if response.status_code == 200:
                    return response.text

                # Log errors for other response statuses
                logging.error(f"Failed to fetch data from ScrapingBee: {response.status_code} - {response.text} on URL: {url}")
                return "Could not load page"

        except httpx.RequestError as e:
            logging.error(f"Error while accessing URL: {url}. Exception: {str(e)}")
            return "Could not load page"
        

    # This function is used to access the top n links and get the raw html content in a async way in orther to increase response time.
    async def access_top_n_links_async(self, results, n = 3):
        """
        Async version
        """
        organic_results = results.get('organic_results', [])
        selected_results = organic_results[:n]
        
        # Create async tasks for all URLs
        async def fetch_content(item):
            try:
                content = await self.access_url_async(url=item['link'], render=False)
                item['parsed_content'] = content
            except Exception as e:
                print(f"Error accessing URL {item['link']}: {e}")
                item['parsed_content'] = ''
        
        # Create tasks for all selected results
        tasks = [fetch_content(item) for item in selected_results]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        return selected_results
        


from readability import Document
from bs4 import BeautifulSoup
import re


# This function is used to clean the html of the top n links, this will get the info ready for the LLM. This part is extremely important! since missing data will kill our workflow.
def html_cleaner(html, top_k_paragraphs = 3) -> list:

    # If the html is empty, due to a failed extraction, we return an empty list.
    if html == '':
        return []
    
    # We use readability to get the summary of the html without useless information that is not relevant to the content
    doc = Document(html)
    clean_html = doc.summary()        # Still HTML but simplified main content
    title = doc.title()
    # Strips all tags to get plain text
    soup = BeautifulSoup(clean_html, "html.parser")
    text = soup.get_text(separator=" ")

    # Further cleaning of the text: This is the simple way, but works for our scope
    text = re.sub(r'\n{2,}', ' ', text) # Changes lineskips of size 2 or more to a single space
    text = '\n'.join([item for item in text.split('\n') if len(item) > 100]) # Filters out lines that are less than 100 characters
    paragraphs = text.split('\n')[:top_k_paragraphs] # Take only the top 5 paragraphs
    
    return paragraphs

    

