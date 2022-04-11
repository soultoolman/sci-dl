# -*- coding: utf-8 -*-
import pytest

from sci_dl import sci_dl


@pytest.fixture
def base_url():
    return 'https://sci-hub.se'


@pytest.fixture
def doi():
    return '10.3390/cancers13153878'


@pytest.fixture
def pmid():
    return '34359786'


@pytest.fixture()
def sh1(base_url):
    return sci_dl.Sci(base_url)


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
            'https': 'socks5://127.0.0.1:1080',
        }

    def test_user_password(self):
        proxy = sci_dl.Proxy(
            protocol='http', user='foo', password='bar;', host='localhost', port=10808
        )
        assert proxy.to_url() == 'http://foo:bar%3B@localhost:10808'


class TestSciHub(object):
    def test_get_protocol(self, sh1):
        assert sh1.get_protocol() == 'https'

    def test_get_matchmaker_url_with_pmid(self, sh1, pmid):
        with pytest.raises(sci_dl.SciDlError):
            sh1.get_matchmaker_url_for_doi(pmid)

    def test_get_matchmaker_url_with_doi(self, sh1, doi):
        url = 'https://sci-hub.se/10.3390/cancers13153878'
        assert sh1.get_matchmaker_url_for_doi(doi) == url

    def test_clean_pdf_url(self, sh1):
        pdf_url = sh1.clean_pdf_url(
            "location.href='/downloads/2021-08-11/f5/gunduz2021.pdf?download=true'"
        )
        assert pdf_url == '/downloads/2021-08-11/f5/gunduz2021.pdf?download=true'

    def test_parse_pdf_url1(self, sh1):
        content = """
        <html>
        <div id = "roll" onclick="rollup()">◂</div>
    <div id = "rollback" onclick="rollback()">
        <img id = "rollimg" src = "/pictures/ravenround.gif">
    </div>
    
    <div id="minu">
        
        <a id = "header" href = "//sci-hub.se/">
            <div>
                <img id = "logo" src = "/pictures/ravenround.gif">
            </div>
            <div>
                <span id = "sci"><span class = "u">sci</span><br>hub</span><br>
                <span id = "motto">to open science</span>
            </div>
        </a>
        
	<div id = "buttons">
            <button onclick = "location.href='/downloads/2021-08-11/f5/gunduz2021.pdf?download=true'">&darr; save</button>
	</div>

	<div id = "citation" onclick = "clip(this)">Gunduz, M., Gunduz, E., Tamagawa, S., Enomoto, K., & Hotomi, M. (2021). <i>Cancer Stem Cells in Oropharyngeal Cancer. Cancers, 13(15), 3878.</i> doi:10.3390/cancers13153878&nbsp;</div>

        <div id = "doi">
            10.3390/cancers13153878
        </div>
        
        <div id ="versions">
            
        </div>
        
    </div>

    <div id="article">
        <embed type="application/pdf" src="/downloads/2021-08-11/f5/gunduz2021.pdf#navpanes=0&view=FitH" id = "pdf"></embed>
    </div>
    </html>
        """
        assert (
            sh1.parse_pdf_url(content)
            == 'https://sci-hub.se/downloads/2021-08-11/f5/gunduz2021.pdf?download=true'
        )

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
