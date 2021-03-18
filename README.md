# :green_book: sci-dl: help you download SciHub PDF programmatically

## Features

1. configuration file support.
2. search by Google Scholar(coming soon).
3. download using DOI.
4. custom SciHub mirror url.
5. proxy support.
6. failure retry.
7. captacha support(coming soon).
7. a Python library that can be embedded in your program.

## Installation

### Windows

coming soon.

### macOS

coming soon.

### Linux

coming soon.

### use pip

```shell
pip install sci-dl
```

### build using setuptools

```shell
git clone https://github.com/soultoolman/sci-dl.git
cd sci-dl
python setup.py install
```

### build using pyinstaller

```shell
pip install pyinstaller
```

```shell
git clone https://github.com/soultoolman/sci-dl.git
cd sci-dl
pyinstaller --name sci-dl -i sci-dl.icns --add-data locale:locale sci_dl.py
# for windows
# pyinstaller --name sci-dl -i sci-dl.icns --add-data locale;locale sci_dl.py
```

## Usage

### use as command line software

1. initialization configuration file

```shell
sci-dl init-config
```

follow the prompt to create the configuration file.

2. download using DOI

```shell
sci-dl dl -d '10.1016/j.neuron.2012.02.004'
# 10.1016/j.neuron.2012.02.004 is the article DOI you want to download
```

### use as Python library

> sci_dl.SciDlError raises when exception happens.

#### if you don't use proxy

```python
from sci_dl import SciHub, Dl


doi = '10.1016/j.neuron.2012.02.004'
sh = SciHub('https://sci-hub.se')
dl = Dl(5)  # 5 is the number of retries when failure

# get matchmaker response
matchmaker_url = sh.get_matchmaker_url('10.1016/j.neuron.2012.02.004')
matchmaker_response = dl.dl(matchmaker_url)

# parse PDF url
pdf_url = sh.parse_pdf_url(matchmaker_response.text)

# get PDF response
pdf_response = dl.dl(pdf_url)

# save PDF content once
with open('xxx', 'wb') as handle:
    handle.write(pdf_response.content)

# save chunk by chunk
chunk_size = 1024
with open('xxx', 'wb') as handle:
    for chunk in pdf_response.iter_content(chunk_size):
        handle.write(chunk)
```

#### if you use a proxy

```python
from sci_dl import SciHub, Dl, Proxy


doi = '10.1016/j.neuron.2012.02.004'
sh = SciHub('https://sci-hub.se')
proxy = Proxy(
    protocol='socks5',
    user=None,
    password=None,
    host='127.0.0.1',
    port=6153
)
dl = Dl(5, proxy=proxy)  # 5 is the number of retries when failure

# get matchmaker response
matchmaker_url = sh.get_matchmaker_url('10.1016/j.neuron.2012.02.004')
matchmaker_response = dl.dl(matchmaker_url)

# parse PDF url
pdf_url = sh.parse_pdf_url(matchmaker_response.text)

# get PDF response
pdf_response = dl.dl(pdf_url)

# save PDF content once
with open('xxx', 'wb') as handle:
    handle.write(pdf_response.content)

# save chunk by chunk
chunk_size = 1024
with open('xxx', 'wb') as handle:
    for chunk in pdf_response.iter_content(chunk_size):
        handle.write(chunk)
```