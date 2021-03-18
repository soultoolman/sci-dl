# -*- coding: utf-8 -*-
"""
sci-dl helps you download SciHub PDF programmatically
"""
import codecs
import logging
import gettext
from os import makedirs
from urllib.parse import urljoin, quote
from os.path import join, exists, dirname, expanduser

import click
import requests
import validators
from bs4 import BeautifulSoup
from rich.console import Console
from yaml import load, dump, Loader, Dumper
from appdirs import user_config_dir, user_log_dir
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

logger = logging.getLogger('sci-dl')
APP_NAME = 'sci-dl'
CONFIG_FILE = join(
    user_config_dir(APP_NAME),
    'sci-dl.yml'
)
DEFAULT_LOG_FILE = join(
    user_log_dir(APP_NAME),
    'sci-dl.log'
)
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/89.0.4389.90 Safari/537.36'
    )
}
DEFAULT_ENCODING = 'utf-8'
DEFAULT_BASE_URL = 'https://sci-hub.se'
MIN_RETRIES = 0
MAX_RETRIES = 50
PROXY_PROTOCOLS = ['socks5', 'http', 'https']
DEFAULT_PROXY_PROTOCOL = 'socks5'
DEFAULT_PROXY_USER = ''
DEFAULT_PROXY_PASSWORD = ''
DEFAULT_PROXY_HOST = '127.0.0.1'
DEFAULT_PROXY_PORT = 1080
CHUNK_SIZE = 128
gettext.install('sci-dl', 'locale')
UNKNOWN_ERROR_MSG = _(
    'Unknown error occurred, please refer to log file to get more detail.'
)


class SciDlError(Exception):
    """SciDlError"""


def is_valid_doi(doi):
    return '/' in doi


progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)


class Proxy(object):
    def __init__(
            self,
            protocol='socks5',
            user='',
            password='',
            host='127.0.0.1',
            port=1080
    ):
        self.protocol = protocol
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def to_url(self):
        if self.user and self.password:
            return '{protocol}://{user}:{password}@{host}:{port}'.format(
                protocol=self.protocol,
                user=self.user,
                password=quote(self.password),
                host=self.host,
                port=self.port
            )
        return '{protocol}://{host}:{port}'.format(
            protocol=self.protocol,
            host=self.host,
            port=self.port
        )

    def __repr__(self):
        return self.to_url()

    def to_requests(self):
        return {
            'http': self.to_url(),
            'https': self.to_url()
        }


class Config(object):
    def __init__(self, data):
        self.data = data

    def get(self, key):
        if key not in self.data:
            raise SciDlError(_("malformed configuration file, can't find %s") % key)
        return self.data[key]

    def set(self, key, value):
        self.data[key] = value

    @classmethod
    def _load(cls, file):
        with codecs.open(file, encoding=DEFAULT_ENCODING) as handle:
            data = load(handle, Loader=Loader)
        return cls(data)

    @classmethod
    def load(cls):
        if not exists(CONFIG_FILE):
            raise SciDlError(
                _(
                    'configuration file %s does not exists, '
                    'please run "sci-dl config init" to create it.'
                ) % CONFIG_FILE
            )
        return cls._load(CONFIG_FILE)

    def _save(self, file):
        directory = dirname(file)
        if not exists(directory):
            makedirs(directory)
        with codecs.open(file, 'w', encoding=DEFAULT_ENCODING) as handle:
            return dump(self.data, handle, Dumper=Dumper)

    def save(self):
        return self._save(CONFIG_FILE)


class Dl(object):
    def __init__(self, retries=3, proxy=None):
        self.retries = retries
        self.proxy = proxy

    def _dl(self, url):
        proxies = self.proxy.to_requests() if self.proxy else None
        return requests.get(
            url,
            headers=HEADERS,
            stream=True,
            proxies=proxies
        )

    def dl(self, url):
        for i in range(self.retries):
            try:
                return self._dl(url)
            except requests.exceptions.RequestException as e:
                logger.exception(e)
                logger.warning(_('retrying...'))
        raise SciDlError(_('download %s failure') % url)


class SciHub(object):
    def __init__(self, base_url):
        self.base_url = base_url

    def get_protocol(self):
        if self.base_url.startswith('https'):
            return 'https'
        return 'http'

    def get_matchmaker_url(self, doi):
        if not is_valid_doi(doi):
            raise SciDlError(_('invalid DOI %s') % doi)
        return urljoin(self.base_url, doi)

    def clean_pdf_url(self, pdf_url):
        # 去除#view=FitH
        if pdf_url[-10:] == '#view=FitH':
            pdf_url = pdf_url[: -10]
        # 有些地址没有协议，现在加上协议
        if not (pdf_url.startswith('https') or pdf_url.startswith('http')):
            pdf_url = '%s:%s' % (self.get_protocol(), pdf_url)
        pdf_url = pdf_url.replace(r'\/', '/')
        return pdf_url

    def parse_pdf_url(self, content):
        soup = BeautifulSoup(content, features='html.parser')
        iframe = soup.find('iframe', id='pdf')
        if (iframe is None) or ('src' not in iframe.attrs):
            return None
        pdf_url = iframe.attrs['src']
        return self.clean_pdf_url(pdf_url)


@click.group()
def sci_dl():
    """
    sci-dl helps you download SciHub PDF programmatically
    """


@sci_dl.command(name='init-config')
def sci_dl_init_config():
    """
    initialize sci-dl configuration
    """
    try:
        console = Console()
        # base_url
        while True:
            base_url = Prompt.ask(
                _(':green_book: SciHub base url'),
                default=DEFAULT_BASE_URL
            )
            if validators.url(base_url):
                break
            console.log(_(':green_book: Invalid base_url %s') % base_url)

        # retries
        while True:
            retries = IntPrompt.ask(
                _(':green_book: Number of failure download retries'),
                default=5
            )
            if MIN_RETRIES <= retries <= MAX_RETRIES:
                break
            console.log(
                _(':green_book: invalid number of failure download retries %s, '
                  'must between %s and %s') % (retries, MIN_RETRIES, MAX_RETRIES)
            )

        # use_proxy
        use_proxy = Confirm.ask(
            _(':green_book: Do you want to use a proxy?'),
            default=True
        )
        proxy_protocol = DEFAULT_PROXY_PROTOCOL
        proxy_user = DEFAULT_PROXY_USER
        proxy_password = DEFAULT_PROXY_PASSWORD
        proxy_host = DEFAULT_PROXY_HOST
        proxy_port = DEFAULT_PROXY_PORT
        if use_proxy:
            # proxy_protocol
            proxy_protocol = Prompt.ask(
                _(':green_book: Protocol of your proxy'),
                choices=PROXY_PROTOCOLS,
                default=DEFAULT_PROXY_PROTOCOL
            )

            # proxy_user
            proxy_user = Prompt.ask(
                _(':green_book: User of your proxy, leave blank if not need'),
                default=DEFAULT_PROXY_USER
            )

            # proxy_password
            proxy_password = Prompt.ask(
                _(':green_book: Password of your proxy, leave blank if not need'),
                password=True, default=DEFAULT_PROXY_PASSWORD,
            )

            # proxy_host
            while True:
                proxy_host = Prompt.ask(
                    _(':green_book: Host of your proxy'),
                    default=DEFAULT_PROXY_HOST
                )
                if validators.domain(
                        proxy_host
                ) or validators.ipv4(
                    proxy_host
                ) or validators.ipv4(proxy_host):
                    break
                console.log(_(':green_book: Invalid host %s') % proxy_host)

            # proxy port
            while True:
                proxy_port = IntPrompt.ask(
                    _(':green_book: Port of your proxy'),
                    default=DEFAULT_PROXY_PORT
                )
                if 1 <= proxy_port <= 65535:
                    break
                console.log(_(':green_book: Invalid port %s, should between 1 and 65535') % proxy_port)

        # log file
        while True:
            log_file = Prompt.ask(
                _(':green_book: Log file'),
                default=DEFAULT_LOG_FILE
            )
            try:
                log_directory = dirname(log_file)
                if not exists(log_directory):
                    makedirs(log_directory)
                break
            except Exception:
                console.log(_(':green_book: Invalid log file %s') % log_file)

        # 输出目录
        while True:
            outdir = Prompt.ask(
                _(':green_book: Where you want to save PDF file'),
                default=expanduser('~')
            )
            if exists(outdir):
                break
            console.log(_(':green_book: Invalid directory %s') % outdir)

        # 是否打开调试模式
        debug_mode = Confirm.ask(
            _(':green_book: Enable DEBUG mode?'),
            default=False
        )
        data = {
            'base_url': base_url,
            'retries': retries,
            'use_proxy': use_proxy,
            'proxy_protocol': proxy_protocol,
            'proxy_user': proxy_user,
            'proxy_password': proxy_password,
            'proxy_host': proxy_host,
            'proxy_port': proxy_port,
            'log_file': log_file,
            'outdir': outdir,
            'debug_mode': debug_mode
        }
        config = Config(data)
        config.save()
        console.log(_(':green_book: Configurations saved, you can edit %s if needed.') % CONFIG_FILE)
    except SciDlError as e:
        logger.exception(e)
        raise click.UsageError(e)
    except Exception as e:
        logger.exception(e)
        raise click.UsageError(UNKNOWN_ERROR_MSG)
    return 0


@sci_dl.command('dl')
@click.option(
    '-d', '--doi', required=True,
    help='DOI, eg, 10.1002/9781118445112.stat06003'
)
def sci_dl_dl(doi):
    """
    download SciHub PDF using DOI
    """
    try:
        config = Config.load()
        if config.get('debug_mode'):
            logging.basicConfig(
                level=logging.DEBUG,
                filename=config.get('log_file')
            )
        else:
            logging.basicConfig(
                filename=config.get('log_file')
            )
        console = Console()
        sh = SciHub(config.get('base_url'))
        if config.get('use_proxy'):
            proxy = Proxy(
                protocol=config.get('proxy_protocol'),
                user=config.get('proxy_user'),
                password=config.get('proxy_password'),
                host=config.get('proxy_host'),
                port=config.get('proxy_port'),
            )
        else:
            proxy = None
        dl = Dl(config.get('retries'), proxy=proxy)
        console.log(_(':green_book: Received DOI [bold][green]%s[/green][/bold]') % doi)

        # get matchmaker url and download the page
        matchmaker_url = sh.get_matchmaker_url(doi)
        matchmaker_response = dl.dl(matchmaker_url)

        # parse PDF url
        pdf_url = sh.parse_pdf_url(matchmaker_response.text)
        if pdf_url is None:
            msg = _('Failed to parse PDF url of DOI %s') % doi
            logger.error(msg)
            raise SciDlError(msg)
        console.log(_(':green_book: Find PDF url %s') % pdf_url)

        # download PDF
        pdf_response = dl.dl(pdf_url)
        content_type = pdf_response.headers['Content-Type']
        if content_type != 'application/pdf':
            msg = _('Failed to Download PDF url %s of DOI %s') % (pdf_url, doi)
            logger.error(msg)
            raise SciDlError(msg)
        content_length = int(pdf_response.headers['Content-Length'])
        fn = '%s.pdf' % doi.replace(r'/', '_')
        file = join(config.get('outdir'), fn)
        task_id = progress.add_task('Download', filename=fn)
        progress.update(task_id, total=content_length)
        with progress, open(file, 'wb') as handle:
            for chunk in pdf_response.iter_content(CHUNK_SIZE):
                handle.write(chunk)
                size = len(chunk)
                progress.update(task_id, advance=size)
        console.log(_(
            ':green_book: Congratulations, PDF was saved to %s successfully.'
        ) % file)
    except SciDlError as e:
        raise click.UsageError(e)
    except Exception as e:
        logger.exception(e)
        raise click.UsageError(UNKNOWN_ERROR_MSG)


if __name__ == '__main__':
    sci_dl()
