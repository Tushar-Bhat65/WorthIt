from selenium import webdriver
from selenium.webdriver.edge.options import Options
import random
import time

def get_edge_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Edge(
        executable_path="C:\\WebDriver\\msedgedriver\\msedgedriver.exe",  # Make sure this path is correct
        options=options
    )
    return driver
