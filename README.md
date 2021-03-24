# sci-dl: help you download SciHub PDF faster

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

### use as command line software

```shell
pip install 'sci-dl[cmd]'
```

### use as Python library

```shell
pip install sci-dl
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

#### if you don't have a proxy

```python
from sci_dl import dl_by_doi


config = {
    'base_url': 'https://sci-hub.se',  # sci-hub URL
    'retries': 5,  # number of failure retries
    'use_proxy': False  # means you don't want to use a proxy
}

response = dl_by_doi('10.1016/j.neuron.2012.02.004', config)
```

### if you use a proxy

```python
from sci_dl import dl_by_doi


config = {
    'base_url': 'https://sci-hub.se',  # sci-hub URL
    'retries': 5,  # number of failure retries
    'use_proxy': True,  # means you don't want to use a proxy
    'proxy_protocol': 'socks5',  # available protocols: http https socks5
    'proxy_user': None,  # proxy user, if your proxy don't need one, you can pass None
    'proxy_password': None,  # proxy password, if your proxy don't need one, you can pass None
    'proxy_host': '127.0.0.1',  # proxy host
    'proxy_port': 1080  # proxy port
}

response = dl_by_doi('10.1016/j.neuron.2012.02.004', config)
```

### how to save response?

#### get all content one time

```python
with open('xxx.pdf', 'wb') as fp:
    fp.write(response.content)
```

#### chunk by chunk

```python
with open('xxx.pdf', 'wb') as fp:
    for chunk in response.iter_content(1024):  # 1024 is the chunk size
        fp.write(chunk)
```