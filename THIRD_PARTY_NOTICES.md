# Third-Party Notices

## Runtime dependency

| Package | Version | License | Purpose | Distribution impact | Decision |
|---|---:|---|---|---|---|
| Cytoscape.js (`cytoscape`) | 3.34.2 | MIT | Browser-based DFG/Process Map rendering and interaction | Bundled into the frontend production assets; MIT notice must be retained | Approved |

The package is used as an npm dependency. No Cytoscape.js implementation or demo source is copied into
this repository. The following notice is retained from the installed `cytoscape@3.34.2` package:

> Copyright (c) 2016-2026, The Cytoscape Consortium.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of
> this software and associated documentation files (the “Software”), to deal in
> the Software without restriction, including without limitation the rights to
> use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
> of the Software, and to permit persons to whom the Software is furnished to do
> so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

## Development-only dependency

| Package | Version | License | Purpose | Distribution impact | Decision |
|---|---:|---|---|---|---|
| Vitest (`vitest`) | 4.1.11 | MIT | Frontend DTO and graph-adapter unit tests | Development/test only; not imported by production source | Approved |

## Backend runtime dependency

| Package | Version | License | Purpose | Distribution impact | Decision |
|---|---:|---|---|---|---|
| Python-Multipart (`python-multipart`) | 0.0.32 | Apache-2.0 | Streaming multipart parsing for local browser file uploads | Included in the backend runtime environment; retain Apache-2.0 license terms | Approved; required by FastAPI `UploadFile` |

## 이번 Phase dependency 결정

새 runtime/development package를 추가하지 않았다. timezone/DST는 기존 DuckDB 1.5.5에 포함된 ICU timezone
기능을 사용하고, HMAC-SHA256은 Python standard library로 pad를 만들고 기존 DuckDB `sha256`/BLOB SQL로
vectorize한다. community crypto extension, `pytz`, PM4Py, background queue dependency는 추가하지 않았다.
