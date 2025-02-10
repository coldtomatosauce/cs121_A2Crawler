import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
# key: word, value: count
words_dict = {}
file = open('stop_words_english.txt', 'r')
data = file.read()
stop_words = data.split('\n')

# key: domain/first_path, value: count
domain_path_dict = {}

all_crawled_urls = []

def scraper(url, resp):
    #f = open("crawled_list.txt", "a")
    #f.write(url + '\n')
    #f.close()
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status != 200:
        return []
    all_crawled_urls.append(resp.url)
    # code from https://beautiful-soup-4.readthedocs.io/en/latest/
    links = []
    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    for link in soup.find_all('a'):
        links.append(link.get('href'))

    valid_links = []
    for link in links:
        if is_valid(link):
            valid_links.append(link)

    links_res = []
    for link in valid_links:
        parsed_url = urlparse(link).geturl()
        if parsed_url in all_crawled_urls: # if link has already been crawled
            break
        text = soup.get_text()
        total_words = len(text.split())
        if total_words < 200: #  if low information value, skip
            break
        if not count_domain_path(link): # if domain and first segment of path is repeated too much, skip
            break

        links_res.append(link)
        count_words(link)

    return links_res


def count_words(text):
    # update words dictionary of word and count
    all_words = text.split()
    for word in all_words:
        if word in words_dict and word not in stop_words:
            words_dict[word] += 1
        elif word not in words_dict and word not in stop_words:
            words_dict[word] = 1

def count_domain_path(url):
    # update domain path dict
    # if count is greater or equal to 50, return false. Otherwise, return true
    parsed = urlparse(url)
    first_path = parsed.path.split('/')[1]
    combined = parsed.netloc + '/' + first_path
    if combined in domain_path_dict:
        if domain_path_dict[combined] > 50:
            return False
        domain_path_dict[combined] += 1
    else:
        domain_path_dict[combined] = 1
    return True

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False
        if not re.match(".*\.(ics.uci.edu|cs.uci.edu|information.uci.edu|stat.uci.edu)$", parsed.netloc.lower()):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|Z|7zip|m4a|webm|rss|apk"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
