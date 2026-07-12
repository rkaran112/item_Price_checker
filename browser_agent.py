#!/usr/bin/env python3
"""
Browser Agent Product Availability Checker
Uses undetected-chromedriver to act as a human user.
Opens a real Chrome browser to bypass advanced WAFs gracefully.
"""

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import re
from urllib.parse import quote_plus
import logging
from datetime import datetime
import os

# Ensure directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', f'browser_agent_search_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BrowserAgentChecker:
    def __init__(self, excel_file_path, output_file_path='product_availability_results.xlsx'):
        self.excel_file_path = excel_file_path
        self.output_file_path = output_file_path
        logger.info("Initializing Agent Browser...")
        
        # Initialize undetected-chromedriver
        options = uc.ChromeOptions()
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1280,1024")
        
        # Start the browser
        self.driver = uc.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def _human_delay(self, min_sec=2, max_sec=5):
        """Simulate human reading/scrolling time"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _get_match_quality(self, excel_brand, excel_title, scraped_title):
        """
        Check if the scraped title from the website is an exact match, 
        a similar match (needs human review), or none.
        Returns: 'exact', 'similar', or 'none'
        """
        base_clean = str(excel_title).lower().strip()
        scraped_clean = str(scraped_title).lower().strip()
        brand_clean = str(excel_brand).lower().strip()

        # A blank title has nothing to match against. Without this guard, an
        # empty string is a substring of everything, and 'nan' (str(float('nan')))
        # is a substring of common words like 'banana' or 'financial', so a
        # blank GeM Title would falsely report 'exact' for any scraped title.
        if base_clean in ('', 'n/a', 'nan'):
            return 'none'

        # 1. Explicit substring match -> EXACT
        if base_clean in scraped_clean:
            return 'exact'
            
        # Tokenize words
        base_words = set(re.findall(r'\w+', base_clean))
        scraped_words = set(re.findall(r'\w+', scraped_clean))
        
        # Exclude very common small words
        stop_words = {'with', 'a', 'an', 'the', 'and', 'for', 'of', 'in'}
        base_words = base_words - stop_words
        
        # 2. Token subset match (do all core words from excel exist in scraped title?) -> EXACT
        if base_words and base_words.issubset(scraped_words):
            return 'exact'
            
        # 3. Check for SIMILAR match
        # If it doesn't match perfectly, but the brand matches and at least some key words match
        brand_in_scraped = (brand_clean not in ('n/a', 'nan', '') and brand_clean in scraped_clean)
        
        # How many significant words overlap?
        word_intersection = base_words.intersection(scraped_words)
        
        # If the brand matches, and we share at least 1 other significant word, consider it "similar"
        # Or if we share at least 30% of the significant words for Google results since titles are truncated
        if len(base_words) > 0:
            match_ratio = len(word_intersection) / len(base_words)
            logger.info(f"[DEBUG] Brand Match: {brand_in_scraped}, Intersection: {len(word_intersection)}, Ratio: {match_ratio:.2f}")
            
            # Very lenient similarity check so we don't miss products
            if (brand_in_scraped and len(word_intersection) >= 2) or (match_ratio >= 0.3):
                # Also if the match ratio is higher, call it exact if > 70% to avoid human review for everything
                if match_ratio >= 0.6:
                    return 'exact'
                return 'similar'
            
        return 'none'

    def search_amazon(self, search_query, excel_brand, excel_title):
        """Search Amazon using human agent with specific title validation"""
        try:
            url = f"https://www.amazon.in/s?k={quote_plus(search_query)}"
            logger.info(f"Agent navigating to Amazon for: {search_query}")
            
            self.driver.get(url)
            self._human_delay(3, 6)
            
            # Wait for search results or 'no results'
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-component-type='s-search-result']")))
            except TimeoutException:
                return {'available': False, 'title': 'No results found', 'price': 'N/A', 'link': None, 'result_count': 0}
                
            results = self.driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
            
            best_similar = None

            # Iterate through the top 5 results to look for a specific title match
            for result in results[:5]:
                try:
                    title_elem = result.find_element(By.TAG_NAME, 'h2')
                    title = title_elem.text.strip()
                except NoSuchElementException:
                    continue
                    
                match_type = self._get_match_quality(excel_brand, excel_title, title)
                if match_type != 'none':
                    try:
                        price_elem = result.find_element(By.CLASS_NAME, 'a-price-whole')
                        price = f"₹{price_elem.text.strip()}"
                    except NoSuchElementException:
                        price = 'N/A'
                        
                    try:
                        link_elem = result.find_element(By.CLASS_NAME, 'a-link-normal')
                        link = link_elem.get_attribute('href')
                    except NoSuchElementException:
                        link = None

                    res_dict = {
                        'available': True,
                        'title': title,
                        'price': price,
                        'link': link,
                        'result_count': len(results),
                        'match_type': match_type
                    }
                    
                    if match_type == 'exact':
                        return res_dict
                    
                    # Store the first similar one
                    if match_type == 'similar' and not best_similar:
                        best_similar = res_dict
                        
            if best_similar:
                return best_similar
                    
            logger.info("Search finished. No specific match found in top 5 results.")    
            return {'available': False, 'title': 'No match found', 'price': 'N/A', 'link': None, 'result_count': 0, 'match_type': 'none'}
                
        except Exception as e:
            logger.error(f"Agent failed on Amazon: {str(e)[:100]}")
            return {'available': False, 'title': 'Error', 'price': 'N/A', 'link': None, 'result_count': 0, 'match_type': 'none'}

    def search_flipkart(self, search_query, excel_brand, excel_title):
        """Search Flipkart using human agent with specific title validation"""
        try:
            url = f"https://www.flipkart.com/search?q={quote_plus(search_query)}"
            logger.info(f"Agent navigating to Flipkart for: {search_query}")
            
            self.driver.get(url)
            self._human_delay(3, 6)
            
            # Close login popup if it appears
            try:
                close_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '✕')]")
                close_btn.click()
            except:
                pass
                
            # Wait for results
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='_1AtVbE' or @class='_2kHMtA' or @class='_13oc-S' or @class='tUxRFH'] | //a[contains(@class, 'VJA3hP')]")))
            except TimeoutException:
                return {'available': False, 'title': 'No results found', 'price': 'N/A', 'link': None, 'result_count': 0, 'match_type': 'none'}
                
            # Grab all links that look like products
            title_xpath = "//a[@class='IRpwTa' or @class='s1Q9rs' or @class='WKTcLC' or contains(@class, 'VJA3hP')] | //div[@class='_4rR01T']"
            titles = self.driver.find_elements(By.XPATH, title_xpath)
            
            price_xpath = "//div[@class='_30jeq3' or @class='_25b18c' or @class='Nx9bqj']"
            prices = self.driver.find_elements(By.XPATH, price_xpath)

            best_similar = None

            # Check up to top 5 results for a specific match
            for idx, title_elem in enumerate(titles[:5]):
                try:
                    title = title_elem.text.strip()
                except:
                    continue
                    
                match_type = self._get_match_quality(excel_brand, excel_title, title)
                if match_type != 'none':
                    # Get link - handle different element types
                    if title_elem.tag_name == 'a':
                        link = title_elem.get_attribute('href')
                    else:
                        try:
                            link_elem = title_elem.find_element(By.XPATH, "./ancestor::a")
                            link = link_elem.get_attribute('href')
                        except:
                            link = None
                            
                    price = prices[idx].text.strip() if idx < len(prices) else 'N/A'
                    
                    res_dict = {
                        'available': True,
                        'title': title,
                        'price': price,
                        'link': link,
                        'result_count': len(titles),
                        'match_type': match_type
                    }
                    
                    if match_type == 'exact':
                        return res_dict
                    
                    if match_type == 'similar' and not best_similar:
                        best_similar = res_dict
                        
            if best_similar:
                return best_similar
                    
            logger.info("Search finished. No specific match found in top 5 results.")
            return {'available': False, 'title': 'No match found', 'price': 'N/A', 'link': None, 'result_count': 0, 'match_type': 'none'}
            
        except Exception as e:
            logger.error(f"Agent failed on Flipkart: {str(e)[:100]}")
            return {'available': False, 'title': 'Error', 'price': 'N/A', 'link': None, 'result_count': 0, 'match_type': 'none'}

    def search_google(self, search_query, excel_brand, excel_title):
        """Search Google using human agent to find the item on any website"""
        try:
            url = f"https://www.google.com/search?q={quote_plus(search_query)}"
            logger.info(f"Agent navigating to Google for: {search_query}")
            
            self.driver.get(url)
            self._human_delay(3, 6)
            
            # Wait for search results
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[.//h3]")))
            except TimeoutException:
                return {'available': False, 'title': 'No results found', 'price': 'N/A', 'link': None, 'match_type': 'none'}
                
            # Find regular organic search results (links that contain an h3 tag)
            links_with_h3 = self.driver.find_elements(By.XPATH, "//a[.//h3]")
            
            # Extract first 3 links to visit
            urls_to_check = []
            for link_elem in links_with_h3:
                if len(urls_to_check) >= 3: break
                try:
                    href = link_elem.get_attribute('href')
                    if href and href not in urls_to_check:
                        urls_to_check.append(href)
                except Exception:
                    continue

            best_similar = None

            # Visit top 3 links and check the content
            for link in urls_to_check:
                try:
                    logger.info(f"Checking link: {link[:80]}...")
                    self.driver.get(link)
                    self._human_delay(2, 4)
                    
                    # Grab the page title and the first h1 to compare
                    page_title = self.driver.title
                    try:
                        h1_tag = self.driver.find_element(By.TAG_NAME, 'h1').text.strip()
                    except:
                        h1_tag = ""

                    # We'll use whichever is longer/more detailed
                    title_to_check = h1_tag if len(h1_tag) > 10 else page_title
                    logger.info(f"[DEBUG] Website Found Title: {title_to_check}")
                    
                    match_type = self._get_match_quality(excel_brand, excel_title, title_to_check)
                    logger.info(f"[DEBUG] match_type assigned: {match_type}")
                    
                    if match_type != 'none':
                        # Extract price using Regex from the page source text (limited to body to avoid massive strings)
                        price = 'N/A'
                        try:
                            body_elem = self.driver.find_element(By.TAG_NAME, "body")
                            # We just grab the first few thousand chars to avoid slow string processing
                            body_text = body_elem.text[:3000]
                            # Regex finds ₹ or Rs followed by digits and commas
                            price_match = re.search(r'(?:₹|INR|Rs\.?)\s*([\d,.]+)', body_text, re.IGNORECASE)
                            if price_match:
                                price = f"₹{price_match.group(1)}"
                        except:
                            pass

                        res_dict = {
                            'available': True,
                            'title': title_to_check,
                            'price': price,
                            'link': link,
                            'match_type': match_type
                        }
                        
                        if match_type == 'exact':
                            return res_dict
                        
                        # Store the first similar one
                        if match_type == 'similar' and not best_similar:
                            best_similar = res_dict
                            
                except Exception as e:
                    logger.error(f"Error checking link {link}: {e}")
                    continue
                        
            if best_similar:
                return best_similar
                    
            logger.info("Search finished. No specific match found in top Google results.")    
            return {'available': False, 'title': 'No match found', 'price': 'N/A', 'link': None, 'match_type': 'none'}
                
        except Exception as e:
            logger.error(f"Agent failed on Google: {str(e)[:100]}")
            return {'available': False, 'title': 'Error', 'price': 'N/A', 'link': None, 'match_type': 'none'}

    def process_products(self):
        """Process products from Excel"""
        try:
            df = pd.read_excel(self.excel_file_path)
            logger.info(f"Agent loaded {len(df)} products")
            results = []
            
            for idx, row in df.iterrows():
                product_id = row.get('GeM Product ID', row.iloc[0] if len(row) > 0 else 'N/A')
                product_title = row.get('GeM Title', row.iloc[1] if len(row) > 1 else 'N/A')
                product_brand = row.get('GeM Brand', row.iloc[2] if len(row) > 2 else 'N/A')
                product_model = row.get('GeM Model', row.iloc[3] if len(row) > 3 else 'N/A')
                
                # Prioritize GeM Model, then GeM Title for the search query
                model_str = str(product_model).strip()
                has_model = model_str.lower() not in ('n/a', 'nan', '')
                search_query = f"{product_model} {product_title}".strip() if has_model else str(product_title)
                logger.info(f"\nProcessing '{search_query}'. Seeking specific match for title: '{product_title}'")
                
                google_res = self.search_google(search_query, product_brand, product_title)
                
                # Check if human review is needed check match type
                needs_review = 'Yes' if google_res.get('match_type') == 'similar' else 'No'
                if google_res.get('match_type') == 'none':
                     needs_review = 'Not Found'
                
                result_row = {
                    'GeM Product ID': product_id,
                    'GeM Title': product_title,
                    'GeM Brand': product_brand,
                    'GeM Model': product_model,
                    'Search Query': search_query,
                    'Needs Human Review': needs_review,
                    'Google Available': 'Yes' if google_res['available'] else 'No',
                    'Google Match Type': google_res.get('match_type', 'none').title(),
                    'Google Title': google_res['title'],
                    'Google Price': google_res['price'],
                    'Google Link': google_res['link'] if google_res['link'] else '',
                }
                
                results.append(result_row)
                
                # Save temp progress
                if (idx + 1) % 5 == 0:
                    pd.DataFrame(results).to_excel(self.output_file_path.replace('.xlsx', '_temp.xlsx'), index=False)

            # Final Save
            results_df = pd.DataFrame(results)
            with pd.ExcelWriter(self.output_file_path, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Product Availability')
            
            logger.info("Agent complete! Results saved.")
            return results_df
            
        except Exception as e:
            logger.error(f"Agent encountered a fatal error: {e}")
        finally:
            # Always close the browser when done
            self.driver.quit()

if __name__ == "__main__":
    print("="*60)
    print("BROWSER AGENT AVAILABILITY CHECKER")
    print("="*60)
    
    excel_file = input("\nEnter Excel file path: ").strip().strip('"').strip("'")
    output_file = input("Enter output file name (press Enter for 'agent_results.xlsx'): ").strip()
    if not output_file: output_file = 'agent_results.xlsx'
    if not output_file.endswith('.xlsx'): output_file += '.xlsx'
    
    output_path = os.path.join('outputs', output_file)
    
    try:
        agent = BrowserAgentChecker(excel_file, output_path)
        agent.process_products()
        print(f"\n✓ Processing complete! Results saved to: {output_path}")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")