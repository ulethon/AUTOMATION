<!-- HEADER / BANNER -->
<h1 align="center" style="margin-bottom:0;">📸 Search Instagram</h1>
<p align="center" style="margin-top:6px;">
  <em>A lightweight Selenium + Brave automation to collect Instagram posts by hashtags/keywords and export clean JSON.</em>
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
        <p>Scrape posts by <strong>#hashtags/keywords</strong>.</p>
      </td>
      <td>
        <h3>🧾 Output</h3>
        <p>Structured <strong>JSON/JSONL</strong> for analysis.</p>
      </td>
      <td>
        <h3>🛡️ Resilient</h3>
        <p>Basic pop-up handling & logging.</p>
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
  <li>🔑 Automated login (Selenium + Brave/Chromium).</li>
  <li>🔍 Search Instagram by <strong>keywords/hashtags</strong>.</li>
  <li>📎 Extracts: post URL, profile name, caption text, found links, matched keyword, dates.</li>
  <li>📄 Appends results to <strong>JSON</strong> (easy to convert to CSV/DB).</li>
  <li>🧭 Infinite scrolling with randomized waits.</li>
  <li>🧰 <code>webdriver-manager</code> auto-installs drivers.</li>
  <li>🛡️ Logging to <code>Instagram_SMS.log</code>.</li>
</ul>

<!-- REQUIREMENTS -->
<h2 id="requirements">📦 Requirements</h2>
<ul>
  <li>Python <strong>3.8+</strong></li>
  <li><strong>Brave</strong> (or Chrome) installed</li>
  <li>Python packages: <code>selenium</code>, <code>webdriver-manager</code></li>
</ul>

<details>
<summary><strong>requirements.txt</strong> (click to expand)</summary>

```txt
selenium
webdriver-manager
</details> <!-- INSTALLATION --> <h2 id="installation">🛠️ Installation</h2> <pre> git clone https://github.com/yourusername/instagram-scraper.git cd search-insta
(optional) virtual environment - python -m venv .venv

Linux/Mac - source .venv/bin/activate
Windows - .venv\Scripts\activate

pip install -r requirements.txt

</pre>

<!-- CONFIGURATION --> <h2 id="configuration">⚙️ Configuration</h2> <p>Create <code>config.ini</code> in the project root:</p>
[creds]
username = your_instagram_username
password = your_instagram_password

<p><strong>Security Tip:</strong> Add <code>config.ini</code> to <code>.gitignore</code> so credentials are never pushed to GitHub.</p> <!-- USAGE --> <h2 id="usage">🚀 Usage</h2> <pre> python instagram_scraper.py -k keywords.txt -t 1.0 -o output.json </pre> <table> <tr><th>Flag</th><th>Description</th><th>Example</th></tr> <tr><td><code>-k</code>, <code>--keywords</code></td><td>Path to file with one keyword/hashtag per line</td><td><code>keywords.txt</code></td></tr> <tr><td><code>-t</code>, <code>--time_limit</code></td><td>Minutes to scroll for each keyword</td><td><code>1.0</code></td></tr> <tr><td><code>-o</code>, <code>--output</code></td><td>Output JSON file</td><td><code>output.json</code></td></tr> </table> <details> <summary><strong>Sample <code>keywords.txt</code></strong></summary>
ryzen3
pcgamer
colombia

</details> <!-- WORKFLOW VISUALIZATION --> <h2 id="workflow">📊 Workflow Visualization</h2> <!-- Mermaid is supported by GitHub in Markdown (works in README). -->
flowchart TD
    A[Start] --> B[Read config.ini]
    B --> C[Login via Selenium]
    C --> D[Read keywords file]
    D --> E[Open hashtag pages]
    E --> F[Scroll & collect post URLs]
    F --> G[Visit post pages]
    G --> H[Extract caption + links]
    H --> I[Append to JSON output]
    I --> J[Write logs & Exit]

<!-- OUTPUT --> <h2 id="output">📄 Example Output (JSON)</h2>
{
  "Cust_ID": "0001",
  "Run_ID": "12345",
  "component-type": "Scrapper",
  "Job_ID": "1234568jack",
  "Source": "Instagram",
  "Source_url": "https://www.instagram.com/p/CosltGfJKfJ/",
  "original_poster_profile": "elingecomputadores",
  "fake_posting_url": "[]",
  "keyword_matched": "ryzen3",
  "original_msg": "elingecomputadores 🤓💻 Actualización PC Gamer con Ryzen 3 3200G ...",
  "post_date": "FEBRUARY 16",
  "finding_date": "2023-06-22 10:08:21"
}

<!-- LOGGING --> <h2 id="logging">📝 Logging</h2> <p>Runtime warnings/errors are saved to <code>Instagram_SMS.log</code>.</p> <details> <summary>Sample log</summary>
2025-08-25 10:05:13,245:WARNING:Login attempt started
2025-08-25 10:05:19,657:WARNING:Successfully logged in
2025-08-25 10:05:46,892:WARNING:Collected 12 posts for keyword: ryzen3
2025-08-25 10:06:21,540:WARNING:Post data saved to output.json

</details> <!-- BEST PRACTICES --> <h2 id="tips">🧠 Best Practices</h2> <ul> <li>Use a secondary account; respect rate limits and platform ToS.</li> <li>Randomize delays; avoid very aggressive scrolling.</li> <li>Keep <code>webdriver-manager</code> and <code>selenium</code> updated.</li> <li>Selectors/XPaths may change; review periodically.</li> <li>Consider rotating proxies if scraping at scale.</li> </ul> <!-- PROJECT STRUCTURE --> <h2>📁 Project Structure</h2> <pre> instagram-scraper/ ├─ instagram_scraper.py ├─ config.ini # not committed (secrets) ├─ requirements.txt ├─ keywords.txt ├─ Instagram_SMS.log # generated └─ output.json # generated </pre> <!-- CREDITS / DISCLAIMER --> <h2 id="credits">🙌 Credits & Disclaimer</h2> <p><strong>Credit:</strong> Full credit goes to <em>ulethon</em>.</p> <p><strong>Disclaimer:</strong> For educational/research use only. Ensure compliance with Instagram’s Terms of Service and local laws. You are responsible for how you use this code.</p> <hr/> <p align="center">Made with ❤️ for clean data collection and learning.</p> ```
