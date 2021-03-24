# -*- coding: utf-8 -*-
"""
sci-dl command line
"""
import json
import codecs
import gettext
import logging
from os import makedirs
from pkg_resources import resource_filename
from os.path import join, exists, dirname, expanduser

import click
import validators
from rich.console import Console
from appdirs import user_config_dir, user_log_dir
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    BarColumn, DownloadColumn, Progress,
    TextColumn, TimeRemainingColumn, TransferSpeedColumn,
)

from .sci_dl import SciDlError, Proxy, Dl, Sci, DEFAULT_ENCODING

# translation configuration
LOCALEDIR = resource_filename('sci_dl', 'locale')
try:
    _ = gettext.translation('sci-dl', LOCALEDIR).gettext
except FileNotFoundError:
    from gettext import gettext as _


APP_NAME = 'sci-dl'
DEFAULT_BASE_URL = 'https://sci-hub.se'
MIN_RETRIES = 0
MAX_RETRIES = 50
CONFIG_FILE = join(
    user_config_dir(APP_NAME),
    'sci-dl.json'
)
DEFAULT_LOG_FILE = join(
    user_log_dir(APP_NAME),
    'sci-dl.log'
)
PROXY_PROTOCOLS = ['socks5', 'http', 'https']
DEFAULT_PROXY_PROTOCOL = 'socks5'
DEFAULT_PROXY_USER = ''
DEFAULT_PROXY_PASSWORD = ''
DEFAULT_PROXY_HOST = '127.0.0.1'
DEFAULT_PROXY_PORT = 1080
CHUNK_SIZE = 128
UNKNOWN_ERROR_MSG = _(
    'Unknown error occurred, please refer to log file to get more detail.'
)
logger = logging.getLogger(APP_NAME)


class Config(dict):
    @staticmethod
    def load(file):
        if not exists(file):
            raise SciDlError(
                _(
                    'configuration file %s does not exists, '
                    'please run "sci-dl init-config" to create it.'
                ) % file
            )
        with codecs.open(file, encoding=DEFAULT_ENCODING) as fp:
            return Config(json.load(fp))

    def get_config(self, key):
        if key not in self:
            raise SciDlError(_("malformed configuration, can't find %s") % key)
        return self[key]

    def write(self, file):
        directory = dirname(file)
        if not exists(directory):
            makedirs(directory)
        with codecs.open(file, 'w', encoding=DEFAULT_ENCODING) as fp:
            return json.dump(self, fp, indent=4)


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
                _('SciHub base url'),
                default=DEFAULT_BASE_URL
            )
            if validators.url(base_url):
                break
            console.log(_('Invalid base_url %s') % base_url)

        # retries
        while True:
            retries = IntPrompt.ask(
                _('Number of failure download retries'),
                default=5
            )
            if MIN_RETRIES <= retries <= MAX_RETRIES:
                break
            console.log(
                _('invalid number of failure download retries %s, '
                  'must between %s and %s') % (retries, MIN_RETRIES, MAX_RETRIES)
            )

        # use_proxy
        use_proxy = Confirm.ask(
            _('Do you want to use a proxy?'),
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
                _('Protocol of your proxy'),
                choices=PROXY_PROTOCOLS,
                default=DEFAULT_PROXY_PROTOCOL
            )

            # proxy_user
            proxy_user = Prompt.ask(
                _('User of your proxy, leave blank if not need'),
                default=DEFAULT_PROXY_USER
            )

            # proxy_password
            proxy_password = Prompt.ask(
                _('Password of your proxy, leave blank if not need'),
                password=True, default=DEFAULT_PROXY_PASSWORD,
            )

            # proxy_host
            while True:
                proxy_host = Prompt.ask(
                    _('Host of your proxy'),
                    default=DEFAULT_PROXY_HOST
                )
                if validators.domain(
                        proxy_host
                ) or validators.ipv4(
                    proxy_host
                ) or validators.ipv4(proxy_host):
                    break
                console.log(_('Invalid host %s') % proxy_host)

            # proxy port
            while True:
                proxy_port = IntPrompt.ask(
                    _('Port of your proxy'),
                    default=DEFAULT_PROXY_PORT
                )
                if 1 <= proxy_port <= 65535:
                    break
                console.log(_('Invalid port %s, should between 1 and 65535') % proxy_port)

        # log file
        while True:
            log_file = Prompt.ask(
                _('Log file'),
                default=DEFAULT_LOG_FILE
            )
            try:
                log_directory = dirname(log_file)
                if not exists(log_directory):
                    makedirs(log_directory)
                break
            except Exception:
                console.log(_('Invalid log file %s') % log_file)

        # 输出目录
        while True:
            outdir = Prompt.ask(
                _('Where you want to save PDF file'),
                default=expanduser('~')
            )
            if exists(outdir):
                break
            console.log(_('Invalid directory %s') % outdir)

        # 是否打开调试模式
        debug_mode = Confirm.ask(
            _('Enable DEBUG mode?'),
            default=False
        )
        config = Config({
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
        })
        config.write(CONFIG_FILE)
        console.log(_('Configurations saved, you can edit "%s" if needed.') % CONFIG_FILE)
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
        config = Config.load(CONFIG_FILE)
        if config.get_config('debug_mode'):
            logging.basicConfig(
                level=logging.DEBUG,
                filename=config.get_config('log_file')
            )
        else:
            logging.basicConfig(
                filename=config.get_config('log_file')
            )
        console = Console()
        sh = Sci(config.get_config('base_url'))
        if config.get_config('use_proxy'):
            proxy = Proxy(
                protocol=config.get_config('proxy_protocol'),
                user=config.get_config('proxy_user'),
                password=config.get_config('proxy_password'),
                host=config.get_config('proxy_host'),
                port=config.get_config('proxy_port'),
            )
        else:
            proxy = None
        dl = Dl(config.get_config('retries'), proxy=proxy)
        console.log(_('Received DOI [bold][green]%s[/green][/bold]') % doi)

        # get matchmaker url and download the page
        matchmaker_url = sh.get_matchmaker_url_for_doi(doi)
        matchmaker_response = dl.dl(matchmaker_url)

        # parse PDF url
        pdf_url = sh.parse_pdf_url(matchmaker_response.text)
        if pdf_url is None:
            msg = _('Failed to parse PDF url of DOI %s') % doi
            logger.error(msg)
            raise SciDlError(msg)
        console.log(_('Find PDF url %s') % pdf_url)

        # download PDF
        pdf_response = dl.dl(pdf_url)
        content_type = pdf_response.headers['Content-Type']
        if content_type != 'application/pdf':
            msg = _('Failed to Download PDF url %s of DOI %s') % (pdf_url, doi)
            logger.error(msg)
            raise SciDlError(msg)
        content_length = int(pdf_response.headers['Content-Length'])
        fn = '%s.pdf' % doi.replace(r'/', '_')
        file = join(config.get_config('outdir'), fn)
        task_id = progress.add_task('Download', filename=fn)
        progress.update(task_id, total=content_length)
        with progress, open(file, 'wb') as fp:
            for chunk in pdf_response.iter_content(CHUNK_SIZE):
                fp.write(chunk)
                size = len(chunk)
                progress.update(task_id, advance=size)
        console.log(_(
            'Congratulations, PDF was saved to %s successfully.'
        ) % file)
    except SciDlError as e:
        logger.exception(e)
        raise click.UsageError(e)
    except Exception as e:
        logger.exception(e)
        raise click.UsageError(UNKNOWN_ERROR_MSG)


if __name__ == '__main__':
    sci_dl()
