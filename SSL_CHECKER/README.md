SSL Certificate Expiry Checker

This Python script checks the expiration date of SSL certificates for a list of domains provided in a text file. It returns a summary of the SSL status for each domain, highlighting those with upcoming expirations.

Features

* Checks SSL certificate expiration dates for multiple domains.
* Outputs results to the console and saves them to a text file.
* Identifies and lists expired certificates or those nearing expiration.

Requirements

* Python 3.x
* OpenSSL (for certificate validation)
* Internet connection (to reach the domains)

Installation

Clone or download this repository.
* Ensure Python 3 is installed on your system.
* Install any required dependencies (if applicable).
* pip install -r requirements.txt  # If a requirements file exists

Usage

1. Create a text file named domains.txt in the same directory as the script.
2. List one domain per line inside domains.txt. Example:
  google.com
  github.com
  example.com

3. cRun the script:
  python ssl_checker.py

4. The script will output SSL information for each domain to the console and save the results in ssl_expiry_report.txt.

Output Example
google.com - Valid (expires on 2025-06-15)
github.com - Valid (expires on 2024-09-12)
example.com - EXPIRED (expired on 2023-10-10)

Customization

* Modify the domain file name or path by changing the script variable for domain input.
* Adjust the expiration warning threshold within the script as needed.

Troubleshooting

* Ensure the domains in domains.txt are reachable.
* Verify the script has permission to access the internet and read the domains.txt file.
* Check for typos in the domain names.
