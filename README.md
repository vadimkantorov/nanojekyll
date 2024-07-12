Hacky primer in Python reimplementation of a subset of [Jekyll](https://jekyllrb.com) and [Liquid](https://shopify.github.io/liquid/) for porting personal blog away from Jekyll.

`nanojekyll` parses Liquid templated and generates Python code, which it then executes to populate the templates. This idea is borrowed from https://github.com/aosabook/500lines/tree/master/template-engine, used as a starting point. The generated Python code can be dumped to a file and inspected.

The supported Liquid language constructs and supported filters are sufficient for rendering [minima Jekyll theme](https://github.com/jekyll/minima)-based blogs.

Example inspired by [jekyll/minima@demo-site](https://github.com/jekyll/minima/tree/demo-site) is in branch [vadimkantorov/nanojekyll@demo-site](../../tree/demo-site) (see [`demo.py`](../../blob/demo-site/demo.py) and [`publish.yml`](../../blob/demo-site/.github/workflows/publish.yml)) and auto-deployed to GitHub Pages at https://vadimkantorov.github.io/nanojekyll/ . Compare to https://jekyll.github.io/minima/.

> [!WARNING]
> This is by no-means a production-ready static blog engine. This is written only to demonstrate how it can be done. In a proper engine, a robust parser for Liquid would be needed and more filters to be reimplemented. An actively developed Python, robust template engine consuming Liquid templates, based on Jinja2 is available at https://github.com/pwwang/liquidpy.

> [!NOTE]
> When deploying to GitHub Pages, do not forget to set `GitHub Actions` as GitHub Pages source in your repo [`Settings -> Pages -> Build and deployment -> Source`](https://github.com/vadimkantorov/nanojekyll/settings/pages). Also do not forget to configure or disable branch protection rule (`No restriction`) in [`Settings -> Environments -> github-pages -> Deployment branches and tags`](https://github.com/vadimkantorov/nanojekyll/settings/environments/).

# Supported [Liquid filters](https://shopify.github.io/liquid/filters/)
TODO: fix lt/gt wrt None; fix type checks of self.ctx; check that or calls `__bool__`, allow extra filters and a single template, code/ctx, unite Template/Context

- `abs`
- `append`
- `at_least`
- `at_most`
- `capitalize`
- `ceil`
- `compact`
- `concat`
- `date`
- `default`
- `divided_by`
- `downcase`
- `escape`
- `escape_once`
- `first`
- `floor`
- `join`
- `last`
- `lstrip`
- `map`
- `minus`
- `modulo`
- `newline_to_br`
- `plus`
- `prepend`
- `remove`
- `remove_first`
- `replace`
- `replace_first`
- `reverse`
- `round`
- `rstrip`
- `size`
- `slice`
- `sort`
- `sort_natural`
- `split`
- `strip`
- `strip_html`
- `strip_newlines`
- `sum`
- `times`
- `truncate`
- `truncatewords`
- `uniq`
- `upcase`
- `url_decode`
- `url_encode`
- `where`

# Supported [Jekyll filters](https://jekyllrb.com/docs/liquid/filters/)
- `relative_url`
- `absolute_url`
- `date_to_xmlschema`
- `date_to_rfc822`
- `date_to_string`
- `date_to_long_string`
- `where_exp`
- `find`
- `find_exp`
- `group_by`
- `group_by_exp`
- `xml_escape`
- `cgi_escape`
- `uri_escape`
- `number_of_words`
- `array_to_sentence_string`
- `markdownify`
- `smartify`
- `sassify`
- `scssify`
- `slugify`
- `jsonify`
- `normalize_whitespace`
- `sort`
- `sample`
- `to_integer`
- `push`
- `pop`
- `shift`
- `unshift`
- `inspect`

# References
- https://aosabook.org/en/500L/a-template-engine.html
- https://github.com/aosabook/500lines/tree/master/template-engine
- https://shuhari.dev/blog/2020/05/500lines-rewrite-template-engine
- https://github.com/shuhari/500lines-rewrite/tree/master/template_engine
- https://gist.github.com/JJediny/a466eed62cee30ad45e2
