# -*- coding: utf-8 -*-
import pytest

import sci_dl


@pytest.fixture
def base_url():
    return 'https://sci-hub.se'


@pytest.fixture
def doi():
    return '10.1002/9781118445112.stat06003'


@pytest.fixture
def pmid():
    return '33692645'


@pytest.fixture()
def sh1(base_url):
    return sci_dl.SciHub(base_url)


def test_is_valid_doi(doi, pmid):
    assert sci_dl.is_valid_doi(doi)
    assert not sci_dl.is_valid_doi(pmid)


class TestProxy(object):
    def test_default(self):
        proxy = sci_dl.Proxy()
        assert proxy.protocol == 'socks5'
        assert proxy.user == ''
        assert proxy.password == ''
        assert proxy.host == '127.0.0.1'
        assert proxy.port == 1080
        assert proxy.to_url() == 'socks5://127.0.0.1:1080'
        assert proxy.to_requests() == {
            'http': 'socks5://127.0.0.1:1080',
            'https': 'socks5://127.0.0.1:1080'
        }

    def test_user_password(self):
        proxy = sci_dl.Proxy(
            protocol='http',
            user='foo',
            password='bar;',
            host='localhost',
            port=10808
        )
        assert proxy.to_url() == 'http://foo:bar%3B@localhost:10808'


class TestSciHub(object):
    def test_get_protocol(self, sh1):
        assert sh1.get_protocol() == 'https'

    def test_get_matchmaker_url_with_pmid(self, sh1, pmid):
        with pytest.raises(sci_dl.SciDlError):
            sh1.get_matchmaker_url(pmid)

    def test_get_matchmaker_url_with_doi(self, sh1, doi):
        url = 'https://sci-hub.se/10.1002/9781118445112.stat06003'
        assert sh1.get_matchmaker_url(doi) == url

    def test_clean_pdf_url(self, sh1):
        pdf_url = sh1.clean_pdf_url(
            r'\/\/sci-hub.se\/downloads\/2020-04-25\/4d\/10.1111@jgs.16467.pdf#view=FitH'
        )
        assert pdf_url == 'https://sci-hub.se/downloads/2020-04-25/4d/10.1111@jgs.16467.pdf'

    def test_parse_pdf_url1(self, sh1):
        content = """
        <html>
            <body>
                <div id="article">
                    <iframe id="pdf" src="//sci-hub.se/downloads/2020-04-25/4d/10.1111@jgs.16467.pdf#view=FitH">
                    </iframe>
                </div>
            </body>
        </html>
        """
        assert sh1.parse_pdf_url(content) == 'https://sci-hub.se/downloads/2020-04-25/4d/10.1111@jgs.16467.pdf'

    def test_parse_pdf_url2(self, sh1):
        content = """
        <html>
            <body>
                <div id="article">
                </div>
            </body>
        </html>
        """
        assert sh1.parse_pdf_url(content) is None
