from selenium import webdriver
from selenium.webdriver.edge.options import Options
import logging

def get_edge_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    try:
        driver = webdriver.Edge(options=options)
        return driver
    except Exception as e:
        logging.error(f"Exception managing MicrosoftEdge: {e}")
        raise
