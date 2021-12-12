import argparse
import csv
import re
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import certifi


TIMEOUT_SECONDS = 10


class SinglePageHTMLParser(HTMLParser):
    def __init__(self, url: str):
        super().__init__(convert_charrefs=True)
        self.__parse_url(url)
        self.links = []
        self.content = ''

        self.__ignore_content = False

    def parse(self):
        try:
            with urlopen(self.url, timeout=TIMEOUT_SECONDS,
                         context=ssl.create_default_context(cafile=certifi.where())) as u:
                self.feed(u.read().decode('utf8'))
        except URLError as e:
            print(f'Cannot access {self.url}: {e}')
        except UnicodeError as e:
            print(f'Invalid encoding for {self.url}: {e}')
        finally:
            # sanitize links
            self.links = [l.rstrip('/') for l in self.links]

    def handle_endtag(self, tag):
        if tag in ['script', 'style']:
            self.__ignore_content = False

    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style']:
            self.__ignore_content = True
            return

        if tag != 'a':
            return

        for attr in attrs:
            if attr[0] == 'href':
                self.__handle_link(attr[1])

    def __handle_link(self, link_value: str):
        if re.search(r'^https?://', link_value) is not None:
            # absolute URL
            self.links.append(link_value)
        else:
            # relative URL
            path = urlparse(link_value).path
            if link_value.startswith('/'):
                # relative to the root of the page
                self.links.append(f'{self.base_url}{path}')
            else:
                # relative to the current directory
                match = re.search(r'(https?://.*)/', self.url)
                current_dir_url = match.group(1) if match else self.url
                self.links.append(f'{current_dir_url}/{path}')

    def handle_data(self, data):
        if not self.__ignore_content:
            self.content += data
            self.links.extend([url for url in re.findall(r'(https?://\S*)', data)])

    def error(self, message):
        print(f'Cannot parse HTML for {self.url}: {message}')

    def __parse_url(self, url: str):
        parsed_url = urlparse(url)
        self.base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        self.url_path = parsed_url.path.rstrip('/')
        self.url = f'{self.base_url}{self.url_path}'


@dataclass
class Page:
    category: str
    URL: str
    text: str

    def to_csv(self, file: str):
        with open(file, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f, dialect='unix').writerow([self.category, self.URL, self.text])

    @staticmethod
    def write_csv_header(file: str):
        with open(file, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f, dialect='unix').writerow(['category', 'URL', 'text'])


def visit_pages(initial_urls: List[str], subpage_limit: int, output_file: str):
    remaining_subpages = {u: subpage_limit for u in initial_urls}
    pages = [Page(u, u, '') for u in initial_urls]

    i = 0
    while i < len(pages):
        html_parser = SinglePageHTMLParser(pages[i].URL)
        html_parser.parse()

        pages[i].text = re.sub(r'\s+', ' ', html_parser.content)
        pages[i].to_csv(output_file)

        for url in html_parser.links:
            parsed_url = urlparse(url)
            base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
            if remaining_subpages.get(base_url, -1) > 0 and url not in [p.URL for p in pages]:
                pages.append(Page(base_url, url, ''))
                remaining_subpages[base_url] -= 1

        i += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='*', metavar='URL', help='initial URLs to visit')
    parser.add_argument('--out', dest='output_file', default='out.csv', help='output file')
    parser.add_argument('--limit', dest='subpage_limit', default=10, help='limit of subpages to save')  # TODO
    args = parser.parse_args()

    initial_urls = [u.rstrip('/') for u in args.url]

    Page.write_csv_header(args.output_file)
    visit_pages(initial_urls, args.subpage_limit, args.output_file)


if __name__ == '__main__':
    main()
