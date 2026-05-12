rule ioc_finder_example{
	meta:
		name = "ioc_finder_example"
		description = "Example IOC-Finder YARA rule (matches legitimate nslookup.exe for demo)"
		reference = "https://github.com/nycthunter/ioc-finder"
	strings:
		$str1 = "nslookup.exe" wide ascii
		$str3 = "nslookup.pdb"
		$str4 = "getaddrinfo"
		$str5 = "/.nslookuprc"
	condition:
		uint16(0) == 0x5a4d and all of them
}