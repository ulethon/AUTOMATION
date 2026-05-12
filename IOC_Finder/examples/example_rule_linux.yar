rule ioc_finder_example{
	meta:
		name = "ioc_finder_example"
		description = "Example IOC-Finder YARA rule (matches legitimate linux 'more' binary for demo)"
		reference = "https://github.com/nycthunter/ioc-finder"
	strings:
		$str1 = "GNU"
		$str3 = "--More--"
		$str4 = "file perusal filter for CRT viewing"
		$str5 = "Press 'h' for instructions"
		$op = { ba 05 00 00 00 31 ff 4? 8d 35 ?? ?? ?? ?? e8 ?? ?? ?? ?? 4? 89 ee 4? 89 c7 e8 ?? ?? ?? ?? ba 05 00 00 00 31 ff 4? 8d 35 ?? ?? ?? ?? e8 ?? ?? ?? ??}
	condition:
		uint16(0) == 0x457f and all of them 
}