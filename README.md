# 简述 #

项目简单实现了一个webserver，包括分发系统，缓存系统，Session系统，模板系统。目前还没有实现form和orm系统。

核心实现没有使用任何第三方库，纯粹作为http原理教学用。和py-web-server属于同一用途。但是由于形成年代教前者晚，因此代码质量相对较高。而且和前者不同的是，其中没有包含greenlet和非阻塞编程框架，默认基于线程模型，也提供可选的 gevent 后端和 web.py WSGI 示例。

# 授权 #

Copyright (C) 2012-2016 Shell Xu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Python 3 与 uv

要求 Python 3.11 或更新版本。在项目目录执行：

```sh
uv sync
uv run webserver
```

配置来自 `serve.conf`，默认监听 8080 端口，使用内置应用和线程后端。
可选依赖：`uv sync --extra gevent` 或 `uv sync --extra webpy`；
分别对应配置中的 `server=gevent` 和 `engine=wsgi`。

```sh
uv sync --all-extras
uv run python -m unittest discover -s tests -v
uv build
```

`tests/` 统一存放所有测试，网络测试仅绑定本机随机端口，并在结束后关闭服务器。
不安装 web.py 时跳过其示例测试。此项目仍定位于 HTTP 教学；
客户端只实现明文 HTTP，模板是可信 Python 代码，Session 超时及
缓存线程同步等原有实现限制尚未完善。
