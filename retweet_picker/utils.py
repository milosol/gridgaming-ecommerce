import re

def id_from_url(url):
    digit = re.search('[\d+]{10,}', url)
    if digit:
        return digit.group(0)
