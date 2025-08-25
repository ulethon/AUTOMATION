<!-- HEADER / BANNER -->
<h1 align="center" style="margin-bottom:0;">📝 Search Quora</h1>
<p align="center" style="margin-top:6px;">
  <em>A Selenium + Brave browser automation script to collect Quora Q&A logs, extract answers, and export structured JSON.</em>
</p>

<!-- BADGES -->
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue">
  <img alt="Selenium" src="https://img.shields.io/badge/Selenium-Automation-success">
  <img alt="License" src="https://img.shields.io/badge/License-Educational--Use--Only-lightgrey">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-informational">
</p>

<!-- CREDIT -->
<p align="center" style="font-size:14px;">
  <strong>Credit Goes To: <span style="color:#e91e63;">ulethon</span></strong>
</p>

<hr/>

<!-- QUICK LOOK CARDS -->
<div align="center">
  <table>
    <tr>
      <td>
        <h3>🔍 Search</h3>
        <p>Scrape questions/answers by <strong>keywords</strong>.</p>
      </td>
      <td>
        <h3>🧾 Output</h3>
        <p>Structured <strong>JSON</strong> for data pipelines.</p>
      </td>
      <td>
        <h3>🛡️ Resilient</h3>
        <p>Login handling + logging to file.</p>
      </td>
    </tr>
  </table>
</div>

<!-- TABLE OF CONTENTS -->
<h2 id="toc">📚 Table of Contents</h2>
<ol>
  <li><a href="#features">Features</a></li>
  <li><a href="#requirements">Requirements</a></li>
  <li><a href="#installation">Installation</a></li>
  <li><a href="#configuration">Configuration</a></li>
  <li><a href="#usage">Usage</a></li>
  <li><a href="#workflow">Workflow Visualization</a></li>
  <li><a href="#output">Example Output</a></li>
  <li><a href="#logging">Logging</a></li>
  <li><a href="#tips">Best Practices</a></li>
  <li><a href="#credits">Credits & Disclaimer</a></li>
</ol>

<!-- FEATURES -->
<h2 id="features">✨ Features</h2>
<ul>
  <li>🔑 Automated login with <strong>username/password</strong> from <code>config.ini</code>.</li>
  <li>🔍 Search Quora questions by <strong>keywords</strong> and <strong>time filters</strong> (hour, day, week, month, year).</li>
  <li>📎 Extracts: Question URL, Answer URLs, full message text, links inside answers.</li>
  <li>📄 Exports results into clean <strong>JSON</strong>.</li>
  <li>🧭 Infinite scrolling until no more results.</li>
  <li>🧰 <code>webdriver-manager</code> auto-handles Brave browser driver.</li>
  <li>🛡️ Error handling and runtime logging in <code>Quora_SMS.log</code>.</li>
</ul>

<!-- REQUIREMENTS -->
<h2 id="requirements">📦 Requirements</h2>
<ul>
  <li>Python <strong>3.8+</strong></li>
  <li><strong>Brave Browser</strong> installed</li>
  <li>Python packages: <code>selenium</code>, <code>webdriver-manager</code></li>
</ul>

<details>
<summary><strong>requirements.txt</strong> (click to expand)</summary>

selenium
webdriver-manager
</details> <!-- INSTALLATION --> <h2 id="installation">🛠️ Installation</h2> <pre> git clone https://github.com/yourusername/quora-scraper.git cd quora-scraper
(optional) virtual environment - python -m venv .venv

Linux/Mac - source .venv/bin/activate
Windows - .venv\Scripts\activate

pip install -r requirements.txt

</pre>

<!-- CONFIGURATION --> <h2 id="configuration">⚙️ Configuration</h2> <p>Create <code>config.ini</code> in the project root:</p>
[creds]
username = your_quora_username
password = your_quora_password

<p><strong>Note:</strong> Never commit this file to version control. Add it to <code>.gitignore</code>.</p> <!-- USAGE --> <h2 id="usage">🚀 Usage</h2> <pre> python quora_scraper.py -k keywords.txt -o output.json -t week </pre> <table> <tr><th>Flag</th><th>Description</th><th>Example</th></tr> <tr><td><code>-k</code>, <code>--keywords</code></td><td>Path to file with one keyword per line</td><td><code>keywords.txt</code></td></tr> <tr><td><code>-o</code>, <code>--output</code></td><td>Output JSON file</td><td><code>output.json</code></td></tr> <tr><td><code>-t</code>, <code>--bytime</code></td><td>Time filter: <code>hour</code>, <code>day</code>, <code>week</code>, <code>month</code>, <code>year</code></td><td><code>week</code></td></tr> </table> <details> <summary><strong>Sample <code>keywords.txt</code></strong></summary>
python selenium
machine learning
data scraping

</details> <!-- WORKFLOW VISUALIZATION --> <h2 id="workflow">📊 Workflow Visualization</h2>
flowchart TD
    A[Start] --> B[Read config.ini]
    B --> C[Login to Quora via Selenium]
    C --> D[Read keywords file]
    D --> E[Search questions by keyword + time filter]
    E --> F[Scroll & collect question URLs]
    F --> G[Visit logs page of each question]
    G --> H[Collect Answer URLs + Message bodies]
    H --> I[Find links inside answers]
    I --> J[Write JSON Output + Log events]

<!-- OUTPUT --> <h2 id="output">📄 Example Output (JSON)</h2>
{
  "Cust_ID": "12345",
  "Run_ID": "000011",
  "component_type": "scrapper",
  "Job_ID": "987644batch01",
  "Source": "Quora",
  "Source_url": "https://www.quora.com/What-is-Python-used-for",
  "fake_posting_url": ["https://example.com"],
  "keyword_matched": "python selenium",
  "original_msg": "Python is widely used for web scraping and automation..."
}

<!-- LOGGING --> <h2 id="logging">📝 Logging</h2> <p>Execution logs are saved into <code>Quora_SMS.log</code>.</p> <details> <summary>Sample log</summary>
2025-07-26 15:08:32,488:ERROR:Login error occurred
Message: no such element: Unable to locate element: {"method":"xpath","selector":"/html/body/div[2]/div/div/div[2]/div/div/div/div[1]/section/main/div/div/div[1]/div[2]/form/div/div[1]/div/label/input"}
  (Session info: chrome=114.0.5735.198)
Stacktrace:
#0 0x55ca9d5a54e3 <unknown>
#1 0x55ca9d2d4c76 <unknown>
#2 0x55ca9d310c96 <unknown>
#3 0x55ca9d310dc1 <unknown>
#4 0x55ca9d34a7f4 <unknown>
#5 0x55ca9d33003d <unknown>
#6 0x55ca9d34830e <unknown>
#7 0x55ca9d32fde3 <unknown>
#8 0x55ca9d3052dd <unknown>
#9 0x55ca9d30634e <unknown>
#10 0x55ca9d5653e4 <unknown>
#11 0x55ca9d5693d7 <unknown>
#12 0x55ca9d573b20 <unknown>
#13 0x55ca9d56a023 <unknown>
#14 0x55ca9d5381aa <unknown>
#15 0x55ca9d58e6b8 <unknown>
#16 0x55ca9d58e847 <unknown>
#17 0x55ca9d59e243 <unknown>
#18 0x7fd5e20c33ec <unknown>

</details> <!-- BEST PRACTICES --> <h2 id="tips">🧠 Best Practices</h2> <ul> <li>Use random delays to reduce chance of blocking.</li> <li>Run with secondary accounts; respect Quora’s ToS.</li> <li>XPath/CSS selectors may change; update periodically.</li> <li>Consider proxies for scale scraping.</li> <li>Validate JSON output with <code>jq</code> or Python <code>json</code> before downstream usage.</li> </ul> <!-- PROJECT STRUCTURE --> <h2>📁 Project Structure</h2> <pre> quora-scraper/ ├─ quora_scraper.py ├─ config.ini # not committed (contains secrets) ├─ requirements.txt ├─ keywords.txt ├─ Quora_SMS.log # generated └─ output.json # generated </pre> <!-- CREDITS / DISCLAIMER --> <h2 id="credits">🙌 Credits & Disclaimer</h2> <p><strong>Credit:</strong> Full credit goes to <em>ulethon</em>.</p> <p><strong>Disclaimer:</strong> For educational purposes only. Ensure compliance with Quora’s Terms of Service and your local laws. Responsibility for use rests solely with the user.</p> <hr/> <p align="center">Built with ❤️ for research and automation learning.</p>
