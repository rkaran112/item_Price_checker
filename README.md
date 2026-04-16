# Browser Agent Product Availability Checker

This project is an automated **Browser Agent** that mimics human browsing behavior to search for product availability across the internet (via Google Search). Its primary goal is to take a bulk list of products (derived from an Excel sheet), search for them online without getting blocked by anti-bot systems (WAFs), evaluate whether the product is a match, and extract its price and link.

---

## ??? How It Works (For Laymen)

Most e-commerce websites (like Amazon, Flipkart, Croma, etc.) have strong security systems that immediately block automated programs from copying their data. They do this by checking if the visitor is a real web browser (like Google Chrome) or a line of code.

To solve this problem, this script uses a specialized driver called **undetected-chromedriver**. 
Instead of sending raw, suspicious code requests, this script actually:
1. **Opens a real, visible Google Chrome window** on your computer.
2. **Types your search queries** into Google.
3. Retrieves the top few organic Search Results.
4. **Visits those websites natively** to check for the product.
5. Uses **NLP (Natural Language Processing)** logic to compare your target product name against the title found on the website.
    * If all major keywords match, it marks it as **Exact Match**.
    * If only some keywords and the brand match, it marks it as **Similar Match** (flagged as "Needs Human Review").
    * If the product is very different, it flags it as **Not Found**.
6. Extracts the price and formats the data cleanly into a brand new Excel sheet.

---

## ?? Project Structure

* **browser_agent.py** : The main brain. Run this file to start the agent!
* **sample_products.xlsx** : The dataset format you should pass into the script. Needs columns like GeM Model and GeM Title.
* **logs/** : This is where the script automatically stores detailed textual logs of every action it performed, what websites it visited, and why it decided an item was (or wasn't) a match. Keep this ignored from Git to avoid clutter.
* **outputs/** : This is where all the generated Excel result files are stored once a search is completed.

*(Note: Data sets, virtual environments (.venv/), and runtime outputs are safely configured in .gitignore so they won't bloat your GitHub repository)*

---

## ?? How to Run

### 1. Prerequisites
Ensure you have Python installed on your computer.
You will also need the standard Google Chrome browser installed on your machine.

### 2. Setup the Environment
It is highly recommended to use a virtual environment so the required packages do not conflict with your main machine.

Open your terminal in the project directory and run:
``bash
# Create the virtual environment
python -m venv .venv

# Activate the virtual environment (Windows)
.\.venv\Scripts\Activate.ps1
``

### 3. Install Dependencies
Once the virtual environment is activated, install the required Python packages:
``bash
pip install -r requirements.txt
# Alternatively, install them manually:
pip install undetected_chromedriver selenium pandas openpyxl
``

### 4. Start the Agent!
Simply run the Python script. It will prompt you for the pathway to your Excel sheet and what you want to name your output.
``bash
python browser_agent.py
``

Sit back, do not close the browser window that opens, and let the agent work! It will take human-style delays between page visits to ensure it is not detected as a bot.
