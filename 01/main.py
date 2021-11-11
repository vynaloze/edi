import argparse
import pathlib
import re
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List
from urllib.parse import urlparse
from urllib.request import urlopen

import certifi


def find_emails(data: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9]+(?:\.[a-zA-Z0-9-]+)*", data)


def to_csv(url: str, kind: str, path: str, content: List[str]):
    sanitized_url = re.sub('[^A-Za-z0-9_-]+', '_', url)
    filename = f'{path}/{sanitized_url}_{kind}.csv'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(','.join(content))


class SinglePageHTMLParser(HTMLParser):
    def __init__(self, url: str):
        super().__init__(convert_charrefs=True)
        self.__parse_url(url)
        self.links = []
        self.emails = []
        self.content = ''

    def parse(self):
        try:
            with urlopen(self.url, context=ssl.create_default_context(cafile=certifi.where())) as u:
                self.feed(u.read().decode('utf8'))
        except Exception as e:
            print(f'Cannot access {self.url}: {e}')

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        for attr in attrs:
            if attr[0] == 'href':
                self.__handle_link(attr[1])

    def __handle_link(self, link_value: str):
        if link_value.startswith('mailto:'):
            emails = find_emails(link_value)
            if len(emails) == 1 and emails[0] not in self.emails:
                self.emails.append(emails[0])
        elif re.search(r'^https?://', link_value) is not None:
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
        self.emails.extend([e for e in set(find_emails(data)) if e not in self.emails])
        self.content += data

    def error(self, message):
        print(f'Cannot parse HTML for {self.url}: {message}')

    def __parse_url(self, url: str):
        parsed_url = urlparse(url)
        self.base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        self.url_path = parsed_url.path
        self.url = f'{self.base_url}{self.url_path}'.rstrip('/')


@dataclass
class Link:
    url: str
    depth: int


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs=1, metavar='URL', help='initial URL to parse')
    parser.add_argument('--depth', dest='depth', default=2, type=int, help='max depth of the crawler')
    parser.add_argument('--output_dir', dest='output_dir', default='out', help='output directory')
    args = parser.parse_args()

    links = [Link(args.url[0], 0)]

    pathlib.Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    i = 0
    while i < len(links):
        html_parser = SinglePageHTMLParser(links[i].url)
        html_parser.parse()

        current_depth = links[i].depth
        for url in html_parser.links:
            if url not in [l.url for l in links] and current_depth < args.depth:
                links.append(Link(url, current_depth + 1))

        to_csv(links[i].url, 'content', args.output_dir, [html_parser.content])
        to_csv(links[i].url, 'emails', args.output_dir, html_parser.emails)

        i += 1


if __name__ == '__main__':
    main()
