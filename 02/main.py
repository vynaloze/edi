import argparse
import re
import ssl
from dataclasses import dataclass, field
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
        self.url_path = parsed_url.path
        self.url = f'{self.base_url}{self.url_path}'.rstrip('/')


@dataclass
class Page:
    url: str
    depth: int
    content: str = ''
    ngrams: List[str] = field(default_factory=lambda: list())
    jaccard_index: float = -1

    def build_ngrams(self, n: int):
        words = self.content.split()
        for i in range(len(words) - (n - 1)):
            self.ngrams.append(' '.join(words[i:i + n]))

    def calculate_jaccard_index(self, reference: 'Page'):
        self.jaccard_index = len([x for x in self.ngrams if x in reference.ngrams]) / len([*reference.ngrams, *self.ngrams])


def build_pages_database(initial_url: str, n_gram_size: int, max_depth: int) -> List[Page]:
    pages = [Page(initial_url.rstrip('/'), 0)]

    i = 0
    while i < len(pages):
        html_parser = SinglePageHTMLParser(pages[i].url)
        html_parser.parse()

        pages[i].content = html_parser.content
        pages[i].build_ngrams(n_gram_size)

        current_depth = pages[i].depth
        if current_depth < max_depth:
            for url in html_parser.links:
                if url not in [l.url for l in pages]:
                    pages.append(Page(url, current_depth + 1))

        i += 1

    return pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs=1, metavar='URL', help='initial URL to parse')
    parser.add_argument('--depth', dest='depth', default=2, type=int, help='max depth of the crawler')
    parser.add_argument('--n-gram-size', dest='n_gram_size', default=2, type=int, help='size of n-grams')
    args = parser.parse_args()

    if args.n_gram_size < 1:
        raise Exception('size of n-grams must be > 0')

    pages = build_pages_database(args.url[0], args.n_gram_size, args.depth)

    reference = pages[0]
    child_pages = pages[1:]
    for page in child_pages:
        page.calculate_jaccard_index(reference)

    child_pages.sort(key=lambda p: p.jaccard_index, reverse=True)

    print('jaccard_index,url')
    for page in child_pages[:3]:
        print(f'{page.jaccard_index},{page.url}')


if __name__ == '__main__':
    main()