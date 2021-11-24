import argparse
import re
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List
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
        except Exception as e:
            print(f'Cannot access {self.url}: {e}')

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
                self.links.append(f'{self.base_url}{path}')
            else:
                self.links.append(f'{self.url}/{path}')

    def handle_data(self, data):
        # TODO find links also here
        if not self.__ignore_content:
            self.content += data

    def error(self, message):
        print(f'Cannot parse HTML for {self.url}: {message}')

    def __parse_url(self, url: str):
        parsed_url = urlparse(url)
        self.base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        self.url_path = parsed_url.path
        self.url = f'{self.base_url}{self.url_path}'.rstrip('/')


@dataclass
class Page:
    url: str
    depth: int
    content: str
    ngrams: List[str]

    def build_ngrams(self, n: int):
        words = self.content.split()
        for i in range(len(words) - (n - 1)):
            self.ngrams.append(' '.join(words[i:i + n]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs=1, metavar='URL', help='initial URL to parse')
    parser.add_argument('--depth', dest='depth', default=2, type=int, help='max depth of the crawler')
    parser.add_argument('--n-gram-size', dest='n_gram_size', default=2, type=int, help='size of n-grams')
    args = parser.parse_args()

    if args.n_gram_size < 1:
        raise Exception('size of n-grams must be > 0')

    pages = [Page(args.url[0], 0, "", [])]

    i = 0
    while i < len(pages):
        html_parser = SinglePageHTMLParser(pages[i].url)
        html_parser.parse()

        pages[i].content = html_parser.content
        pages[i].build_ngrams(args.n_gram_size)

        current_depth = pages[i].depth
        if current_depth < args.depth:
            for url in html_parser.links:
                if url not in [l.url for l in pages]:
                    pages.append(Page(url, current_depth + 1, "", []))

        i += 1

    print(pages)


if __name__ == '__main__':
    main()
