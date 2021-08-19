# -*- coding: utf-8 -*-
"""
sci-dl helps you download SciHub PDF faster
"""
import logging
from gettext import gettext as _
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('sci-dl')
DEFAULT_ENCODING = 'UTF-8'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/89.0.4389.90 Safari/537.36'
    )
}
DEFAULT_CONFIG = {
    'base_url': 'https://sci-hub.se',
    'retries': 5,
    'use_proxy': False
}


class SciDlError(Exception):
    """SciDlError"""


def is_valid_doi(doi):
    return '/' in doi


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
            except Exception as e:
                logger.exception(e)
                logger.warning(_('retrying...'))
        raise SciDlError(_('download %s failure') % url)


class Sci(object):
    def __init__(self, base_url):
        self.base_url = base_url

    def get_protocol(self):
        if self.base_url.startswith('https'):
            return 'https'
        return 'http'

    def get_matchmaker_url_for_doi(self, doi):
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
        iframe = soup.find('embed', id='pdf')
        if (iframe is None) or ('src' not in iframe.attrs):
            return None
        pdf_url = iframe.attrs['src']
        return self.clean_pdf_url(pdf_url)


def dl_by_doi(doi, config=None):
    """
    download PDF by DOI

    Args:
        doi: <str> DOI
        config: <dict> must contains the following keys:
            when you have a proxy:
                1. base_url: <str> SciHub url, eg, https://sci-hub.se
                2. retries: <int> number of failure retries, eg, 5
                3. use_proxy: <bool> use proxy or not, eg, True
                4. proxy_protocol: <str> proxy protocol, eg, socks5
                5. proxy_user: <str> proxy username, None if no user need
                6. proxy_password: <str> proxy password, None if no password need
                7. proxy_host: <str> proxy host, eg, 127.0.0.1
                8. proxy_port: <int> proxy port, eg, 1080
            when you don't have a proxy:
                1. base_url: <str> SciHub url, eg, https://sci-hub.se
                2. retries: <int> number of failure retries, eg, 5
                3. use_proxy: <bool> use proxy or not, eg, False
            default:
                {
                    "base_url": "https://sci-hub.se",
                    "retries": 5,
                    "user_proxy": False
                }
    Returns:
        requests.models.Response
    Raises:
        SciDlError
    """
    def get(key):
        if key not in config:
            raise SciDlError(_("malformed configuration, can't find %s") % key)
        return config[key]

    if config is None:
        config = DEFAULT_CONFIG.copy()

    # initialize objects
    sci = Sci(get('base_url'))
    proxy = None
    if get('use_proxy'):
        proxy = Proxy(
            protocol=get('proxy_protocol'),
            user=get('proxy_user'),
            password=get('proxy_password'),
            host=get('proxy_host'),
            port=get('proxy_port')
        )
    dl = Dl(get('retries'), proxy)

    # get matchmaker url
    matchmaker_url = sci.get_matchmaker_url_for_doi(doi)
    # download matchmaker response
    matchmaker_response = dl.dl(matchmaker_url)
    # get parse pdf url
    pdf_url = sci.parse_pdf_url(matchmaker_response.content)
    if not pdf_url:
        raise SciDlError(_('Failed to parse PDF url of DOI %s') % doi)
    # download pdf response
    return dl.dl(pdf_url)
