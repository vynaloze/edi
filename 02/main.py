import argparse
import re
import ssl
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import certifi
import numpy as np

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
    url: str
    depth: int
    content: str = ''
    ngrams: List[str] = field(default_factory=lambda: list())
    similarity: float = -1

    def build_ngrams(self, n: int, bag_of_words: bool):
        words = self.content.split()
        for i in range(len(words) - (n - 1)):
            self.ngrams.append(' '.join(words[i:i + n]))
        if bag_of_words:
            self.ngrams = list(set(self.ngrams))

    def calculate_jaccard_index(self, reference: 'Page'):
        intersection = [x for x in self.ngrams if x in reference.ngrams]
        union = [*reference.ngrams, *self.ngrams]
        self.similarity = len(intersection) / len(union)

    def calculate_cosine_distance(self, reference: 'Page'):
        domain = list(set(self.ngrams).union(set(reference.ngrams)))
        vector_this = [int(ngram in self.ngrams) for ngram in domain]
        vector_reference = [int(ngram in reference.ngrams) for ngram in domain]
        self.similarity = \
            np.dot(vector_this, vector_reference) / (np.linalg.norm(vector_this) * np.linalg.norm(vector_reference))


def build_pages_database(initial_url: str, n_gram_size: int, max_depth: int, bag_of_words: bool) -> List[Page]:
    pages = [Page(initial_url.rstrip('/'), 0)]

    i = 0
    while i < len(pages):
        html_parser = SinglePageHTMLParser(pages[i].url)
        html_parser.parse()

        pages[i].content = html_parser.content
        pages[i].build_ngrams(n_gram_size, bag_of_words)

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
    parser.add_argument('algorithm', choices=['jaccard_index', 'cosine_distance'], help='similarity algorithm to use')
    parser.add_argument('--depth', dest='depth', default=2, type=int, help='max depth of the crawler')
    parser.add_argument('--n-gram-size', dest='n_gram_size', default=2, type=int, help='size of n-grams')
    parser.add_argument('--bag-of-words', dest='bag_of_words', action='store_true', help='use bag-of-words mode')
    args = parser.parse_args()

    if args.depth < 1:
        raise Exception('depth must be > 0')
    if args.n_gram_size < 1:
        raise Exception('size of n-grams must be > 0')

    pages = build_pages_database(args.url[0], args.n_gram_size, args.depth, args.bag_of_words)

    reference = pages[0]
    child_pages = pages[1:]
    for page in child_pages:
        if args.algorithm == 'jaccard_index':
            page.calculate_jaccard_index(reference)
        elif args.algorithm == 'cosine_distance':
            page.calculate_cosine_distance(reference)

    child_pages.sort(key=lambda p: p.similarity, reverse=True)

    print(f'{args.algorithm},url')
    for page in child_pages[:3]:
        print(f'{page.similarity},{page.url}')


if __name__ == '__main__':
    main()
