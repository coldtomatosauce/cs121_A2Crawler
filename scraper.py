import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from itertools import islice

# key: word, value: count
words_dict = {}
file = open('stop_words_english.txt', 'r')
data = file.read()
stop_words = data.split('\n')

# key: domain/first_path, value: count
domain_path_dict = {}
# len of this is the number of unique pages
crawled_links = set()
added_frontier_links = set()
# url with most number of words
longest_page = ["none", 0]

# key: subdomain, value: count
ics_subdomains_dict = {} # for report
cs_subdomains_dict = {}
info_subdomains_dict = {}
stat_subdomains_dict = {}

def scraper(url, resp):
    write_report(url)
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

    # if status is client error or server error, do not crawl link
    if resp.status >= 400:
        append_to_file("skipped_list.txt", resp.url, True)
        return []

    # code from https://beautiful-soup-4.readthedocs.io/en/latest/
    # get text from link
    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    text = soup.get_text()

    # decide to crawl link
    crawled_links.add(resp.url)
    append_to_file("all_crawled_list.txt", resp.url, False)

    # count words & update word dict
    total_words = len(tokenize(text))
    if total_words > longest_page[1]:
        longest_page[0] = resp.url
        longest_page[1] = total_words

    # update subdomain count
    cur_parsed_url = urlparse(resp.url)._replace(fragment="")
    #cur_clean_link = cur_parsed_url.geturl()
    count_subdomain(cur_parsed_url)

    # extract links
    links = []
    for link in soup.find_all('a'):
        links.append(link.get('href'))

    valid_links = []
    for link in links:
        if is_valid(link):
            valid_links.append(link)

    links_res = []
    append_to_file("frontier_list.txt", resp.url, False)

    for link in valid_links:
        parsed_url = urlparse(link)._replace(fragment="")
        clean_link = parsed_url.geturl()
        # if link has already been or will be crawled, skip this link
        if clean_link in crawled_links or clean_link in added_frontier_links:
            continue
        # if domain and first segment of path is repeated over the threshold, skip this link
        if not is_below_count_domain_path(parsed_url):
            append_to_file("skipped_list.txt", clean_link, False)
            continue
        # decided link will be added to frontier
        added_frontier_links.add(clean_link)
        append_to_file("frontier_list.txt", clean_link, True)
        links_res.append(clean_link)

    return links_res

def append_to_file(o_file, link, is_tab):
    # append link to output file. if is_tab is true, will write a tab in front
    f = open(o_file, "a")
    if is_tab:
        f.write('\t')
    f.write(link + '\n')
    f.close()

def write_report(url):
    # write to file a report
    report = open("report.txt", "w")
    report.write("number of unique pages: " + str(len(crawled_links)) + '\n')
    report.write("\nlongest page: " + longest_page[0] + ", words: " + str(longest_page[1]) + '\n')
    report.write("\nics subdomains:\n")
    for sub, count in ics_subdomains_dict.items():
        report.write("\t" + sub + ": " + str(count) + '\n')
    report.write("\ncs subdomains:\n")
    for sub, count in cs_subdomains_dict.items():
        report.write("\t" + sub + ": " + str(count) + '\n')
    report.write("\ninformatics subdomains:\n")
    for sub, count in info_subdomains_dict.items():
        report.write("\t" + sub + ": " + str(count) + '\n')
    report.write("\nstat subdomains:\n")
    for sub, count in stat_subdomains_dict.items():
        report.write("\t" + sub + ": " + str(count) + '\n')

    sorted_dict = [(v, k) for k, v in words_dict.items()]
    sorted_dict.sort(reverse=True)
    report.write("\nsorted words:\n")
    for i, (count, word) in enumerate(islice(sorted_dict, 50)):
        report.write(str(i + 1) + ". "+ word + ": " + str(count) + '\n')
    report.close()

def count_subdomain(parsed_url):
    # update counts of subdomains
    subdomain = parsed_url.netloc.lstrip('w.').split('.')[0]
    if re.match(".*(ics.uci.edu)$", parsed_url.netloc):
        if subdomain == "ics":
            return
        update_count(subdomain, ics_subdomains_dict)
    elif re.match(".*(cs.uci.edu)$", parsed_url.netloc):
        if subdomain == "cs":
            return
        update_count(subdomain, cs_subdomains_dict)
    elif re.match(".*(informatics.uci.edu)$", parsed_url.netloc):
        if subdomain == "informatics":
            return
        update_count(subdomain, info_subdomains_dict)
    elif re.match(".*(stat.uci.edu)$", parsed_url.netloc):
        if subdomain == "stat":
            return
        update_count(subdomain, stat_subdomains_dict)

def update_count(key, dictionary):
    if key in dictionary:
        dictionary[key] += 1
    else:
        dictionary[key] = 1

def tokenize(text):
    # return list of tokens in text
    tokens = set()
    text = text.lower()
    # using regex, replace all non-alphanumeric characters with space
    text = re.sub(r"[^a-zA-Z0-9]", " ", text)
    for word in text.split():
        if word not in stop_words:
            tokens.add(word)
            update_count(word, words_dict)
    tokens = list(tokens)
    return tokens

def is_below_count_domain_path(parsed_url):
    # update domain path dict
    # if count is greater or equal to 50, return false. Otherwise, return true
    path_split = parsed_url.path.split('/')
    if len(path_split) <= 1:
        return True
    first_path = path_split[1]
    combined = parsed_url.netloc + '/' + first_path
    if combined in domain_path_dict:
        if domain_path_dict[combined] > 100:
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
        if not re.match(".*(ics.uci.edu|cs.uci.edu|informatics.uci.edu|stat.uci.edu)$", parsed.netloc.lower()):
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
