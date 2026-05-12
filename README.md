<!-- HEADER -->
<h1 align="center">🤖 CTI-AUTOMATION</h1>
<p align="center">
  <em>A collection of automation & scraping scripts for different platforms</em>
</p>

<!-- BADGES -->
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white">
  <img alt="Selenium" src="https://img.shields.io/badge/Selenium-Automation-success?logo=selenium&logoColor=white">
  <img alt="Platforms" src="https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-informational">
  <img alt="License" src="https://img.shields.io/badge/License-Educational--Only-lightgrey">
</p>

<hr/>

<!-- PROJECT OVERVIEW -->
<h2>📌 Overview</h2>
<p>
This repository serves as a centralized hub for multiple automation scripts.  
Each script is self-contained in its own folder with a dedicated <code>README.md</code> for setup, usage, and workflow explanation.  
More scripts will be added in the future 🚀
</p>

<hr/>

<!-- REPO STRUCTURE -->
<h2>📂 Repository Structure</h2>
AUTOMATION/<br>
├─ Search_Insta/     # Instagram automation script<br>
├─ Search_Quora/     # Quora automation script<br>
├─ New_Script/       # (Future scripts will go here)<br>
└─ README.md         # This hub documentation<br>
<hr/> <!-- AVAILABLE SCRIPTS --> <h2>📜 Available Scripts</h2> <p>Click on any script to view detailed documentation & usage.</p> <ul> <li>📷 <a href="./Search_Insta/README.md"><strong>Instagram Scraper</strong></a></li> <li>📝 <a href="./Search_Quora/README.md"><strong>Quora Scraper</strong></a></li> <!-- Add new scripts below as the repo grows --> </ul> <hr/> <!-- FEATURES --> <h2>✨ Core Features Across Scripts</h2> <table> <tr> <td><h3>🔑 Authentication</h3><p>Automated login with config-based credentials.</p></td> <td><h3>🔍 Search</h3><p>Keyword, hashtag, or time-based filtering.</p></td> <td><h3>📄 Export</h3><p>Outputs structured <code>JSON</code> data.</p></td> </tr> <tr> <td><h3>🛡️ Logging</h3><p>Error & activity logs in <code>.log</code> files.</p></td> <td><h3>⚙️ Selenium</h3><p>Automation using Brave + WebDriver Manager.</p></td> <td><h3>📊 Visualization</h3><p>Mermaid workflow diagrams included in docs.</p></td> </tr> </table> <hr/> <!-- WORKFLOW --> <h2>📊 General Workflow</h2>
flowchart TD
    A[Start] --> B[Select Script]<br>
    B -->|Instagram| C[Login & Collect Posts]<br>
    B -->|Quora| D[Login & Collect Q&A]<br>
    B -->|Future Scripts| H[Execute Platform Logic]<br>
    C --> E[Extract Fields]<br>
    D --> E[Extract Fields][Start] --> B[Select Script]<br>
    H --> E<br>
    E --> F[Store as JSON]<br>
    F --> G[Save Logs + Output]<br>
    G --> I[End]<br>

<hr/> <!-- GETTING STARTED --> <h2>⚡ Getting Started</h2> <ol> <li><strong>Clone the repository</strong> <pre>git clone https://github.com/yourusername/AUTOMATION.git</pre> </li> <li><strong>Navigate to a script folder</strong> Example: <code>cd Search_Insta</code> </li> <li><strong>Follow the setup in that folder’s README</strong> to install dependencies & run.</li> </ol> <hr/> <!-- CONTRIBUTIONS --> <h2>🤝 Contributions</h2> <p> This repo is designed to grow. If you wish to add a new automation script, simply create a folder, include your code + a <code>README.md</code>, and update the main list above. </p> <hr/> 
<p align="center">Made with ❤️ for automation learning & scalability</p>
