# TODO: impl filters, fixup first/last, delete prefix _

import os, sys, re, html, json, datetime
import inspect

class NanoJekyllTemplate:
    @staticmethod
    def read_template(path, front_matter_sep = '---\n'):
        front_matter, template = '', ''
        with open(path) as f:
            line = f.readline()
            if line == front_matter_sep:
                front_matter += front_matter_sep
                while (line := f.readline()) != front_matter_sep:
                    front_matter += line
                front_matter += front_matter_sep
            else:
                template += line
            template += f.read()
        return front_matter, template

    @staticmethod
    def codegen(templates, includes = {}, global_variables = [], plugins = {}, newline = '\n'):
        indent_level = 1

        python_source  = 'import os, sys, re, html, json, datetime' + newline
        python_source += inspect.getsource(NanoJekyllContext) + newline
        python_source += ' ' * 4 * indent_level + 'includes = ' + repr(includes) + newline
        python_source += newline.join(str(NanoJekyllTemplate(template_name = template_name, template_code = template_code, includes = includes, global_variables = global_variables, indent_level = indent_level, plugins = list(plugins))) for template_name, template_code in templates.items()) + newline
        python_source += newline.join(str(Plugin(template_name = 'plugin_' + plugin_name, includes = includes, global_variables = global_variables, indent_level = indent_level)) for plugin_name, Plugin in plugins.items()) + newline
        
        try:
            global_namespace = {}
            exec(python_source, global_namespace)
            cls = global_namespace[NanoJekyllContext.__name__] 
        except Exception as e:
            print(e)
            cls = None

        return cls, python_source
  
    def __init__(self, template_name = '', template_code = '', includes = {}, global_variables = [], plugins = [], indent_level = 0):
        self.includes = includes
        self.global_variables = global_variables
        self.plugins = plugins

        self.code = []
        self.indent_level = indent_level
    
        split_tokens = lambda s: re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", s)
        # https://shopify.github.io/liquid/tags/iteration/#forloop-object

        function_name = NanoJekyllContext.sanitize_template_name(template_name)
        self.add_line(f'def render_{function_name}(self):')
        self.indent_level += 1
        self.add_line('''nil, false, true, forloop, result = None, False, True, self.forloop, []''')

        filters_names = [k for k in dir(NanoJekyllContext) if (k.startswith('_') and not k.startswith('__')) and (k.endswith('_') and not k.endswith('__'))]
        self.add_line((', '.join(k.removeprefix('_').removesuffix('_') for k in filters_names) or '()') + ' = ' + ((', '.join(f'self.pipify(self.{k})' for k in filters_names) or '()')))
        self.add_line((', '.join(self.global_variables) or '()') + ' = ' +  (', '.join(NanoJekyllContext.__name__ + f'(self.ctx.get({k!r}))' for k in self.global_variables) or '()') )

        template_code = template_code or getattr(self, 'template_code', '')
        tokens = split_tokens(template_code)
        
        ops_stack = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            b = 3 if token.startswith('{%-') or token.startswith('{{-') else 2
            e = -3 if token.endswith('-%}') or token.endswith('-}}') else -2
            token_inner = token[b:e].strip()
            words = token_inner.split()
            
            if b == 3:
                self.add_line("result.append(self.TrimLeft())")

            if token.startswith('{{'):
                expr = self._expr_code(token_inner)
                self.add_line(f"result.append(str({expr}))")

            elif token.startswith('{%'):
                if words[0] == '-':
                    del words[0]
                if words[-1] == '-':
                    del words[-1]

                if words[0] == 'comment':
                    tokens_i_end = tokens[i].replace(' ', '').replace('comment', 'endcomment')
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        i += 1
    
                elif words[0] == 'highlight':
                    lang = ''.join(words[1:])
                    self.add_line(f'result.append("\\n```{lang}\\n")')
                    tokens_i_end = '{%endhighlight%}'
                    i += 1
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        self.add_line('result.append(' + repr(tokens[i]) + ')')
                        i += 1
                    self.add_line('result.append("\\n```\\n")')

                elif words[0] == 'if':
                    ops_stack.append('if')
                    self.add_line("if {}:".format(' '.join(words[1:])))
                    self.indent_level += 1
                
                elif words[0] == 'elsif':
                    self.indent_level -= 1
                    self.add_line("elif {}:".format(' '.join(words[1:])))
                    self.indent_level += 1
                
                elif words[0] == 'else':
                    #ops_stack.append('else')
                    self.indent_level -= 1
                    self.add_line("else:".format(' '.join(words[1:])))
                    self.indent_level += 1
                
                elif words[0] == 'unless':
                    ops_stack.append('unless')
                    self.add_line("if not( {} ):".format(' '.join(words[1:])))
                    self.indent_level += 1
                
                elif words[0] == 'for':
                    assert len(words) == 4 and words[2] == 'in', f'Dont understand for: {token=}'
                    ops_stack.append('for')
                    self.add_line('for {} in {}:'.format(words[1], self._expr_code(words[3]) ) )
                    self.indent_level += 1
                
                elif words[0].startswith('end'):
                    # Endsomething.  Pop the ops stack.
                    assert len(words) == 1, f'Dont understand end: {token=}'
                    end_what = words[0][3:]
                    assert ops_stack, f'Too many ends: {token=}'
                    start_what = ops_stack.pop()
                    assert start_what == end_what, f'Mismatched end tag: {start_what=} != {end_what=}'
                    self.indent_level -= 1

                elif words[0] == 'include':
                    template_name = words[1]
                    beg = None
                    if len(words) > 2 and '=' in words:
                        beg = ([k for k, w in enumerate(words) if w == '='] or [0])[0] - 1
                        self.add_line('include=' +  NanoJekyllContext.__name__ + '(dict(' + ', '.join(words[k] + words[k + 1] + words[k + 2] for k in range(beg, len(words), 3)) + '))')
                    template_name = ' '.join(words[1:beg])

                    if '{{' not in template_name and '}}' not in template_name:
                        frontmatter_include, template_include = self.includes[template_name]
                        tokens = tokens[:i + 1] + split_tokens(template_include) + tokens[i + 1:]
                    else:
                        template_name = ' '.join(words[1:]).replace('{{', '{').replace('}}', '}')
                        template_name = 'f' + repr(template_name)
                        self.add_line('include_name = ' + template_name)
                        self.add_line('result.append(self.includes[include_name][-1])')
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    self.add_line('{} = {}'.format(var_name, expr))

                elif words[0] in plugins: 
                    template_name = words[0]
                    self.add_line(f'assert bool(self.render_plugin_{template_name}); tmp = self.render_plugin_{template_name}(); (result.extend if isinstance(tmp, list) else result.append)(tmp)')
                else:
                    assert False, ('Dont understand tag: ' + words[0])

            else:
                if token:
                    self.add_line("result.append({})".format(repr(token)))
            
            if e == -3:
                self.add_line('result.append(self.TrimRight())')
            i += 1

        assert not ops_stack, ('Unmatched action tag: ' + ops_stack[-1])

        self.add_line('return self.finalize_result(result)')
    
    def _expr_code(self, expr):
        is_string_literal = lambda expr: (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'"))
        expr = expr.strip()

        if is_string_literal(expr):
             code = expr

        elif '|' in expr:
            pipes = list(map(str.strip, expr.split('|')))
            code = NanoJekyllContext.__name__+ '(' + self._expr_code(pipes[0]) + ')' if is_string_literal(pipes[0]) else self._expr_code(pipes[0])
            for func in pipes[1:]:
                func_name, *func_args = func.split(':', maxsplit = 1)
                
                if not func_args:
                    code = f'{code} | {func_name}()'
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    code = f'{code} | {func_name}({func_args})'
                    
        else:
            code = expr

        return code

    def __str__(self):
        return ''.join(map(str, self.code)) 

    def add_line(self, line = ''):
        self.code.extend([' ' * 4 * self.indent_level, line, "\n"])

class NanoJekyllContext:
    class forloop: index = 1; last = False; first = False; index0 = 0; length = None; rindex = -1;
    class TrimLeft(str): pass
    class TrimRight(str): pass
    
    def __init__(self, ctx = None, metafunction = None):
        # https://shopify.github.io/liquid/basics/operators/
        self.ctx = ctx.ctx if isinstance(ctx, NanoJekyllContext) else ctx
        self.metafunction = metafunction
    
    def __or__(self, other):
        return NanoJekyllContext(other[0](self.ctx, *other[1:]))

    def __str__(self):
        return str(self.ctx) if self.ctx else ''

    def __bool__(self):
        return bool(self.ctx)

    def __gt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx > other

    def __ge__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx >= other

    def __lt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx < other

    def __le__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx <= other

    def __eq__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx == other

    def __ne__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx != other
        
    def __getattr__(self, key):
        if isinstance(self.ctx, dict):
            if key in self.ctx:
                return NanoJekyllContext(self.ctx[key])
        return NanoJekyllContext(getattr(self.ctx, key, None))
    
    def __getitem__(self, index):
        if isinstance(self.ctx, (list, str)):
            return NanoJekyllContext(self.ctx[index])
        if isinstance(self.ctx, dict):
            return NanoJekyllContext(self.ctx.get(index))
        return NanoJekyllContext(None)

    def __len__(self):
        return len(self.ctx) if isinstance(self.ctx, (list, dict, str)) else None

    def __iter__(self):
        yield from (map(NanoJekyllContext, self.ctx) if self.ctx else [])

    @staticmethod
    def pipify(f):
        return (lambda *args: (f, *args))
        
    @staticmethod
    def finalize_result(result):
        # https://shopify.github.io/liquid/basics/whitespace/
        res = ''
        trimming = False
        for s in result:
            if isinstance(s, NanoJekyllContext.TrimLeft):
                res = res.rstrip()
            elif isinstance(s, NanoJekyllContext.TrimRight):
                trimming = True
            else:
                if trimming:
                    s = s.lstrip()
                if s:
                    res += s
                    trimming = False
        return res
    
    @staticmethod
    def sanitize_template_name(template_name):
        return os.path.splitext(template_name)[0].translate({ord('/') : '_', ord('-'): '_', ord('.') : '_'})

    def render(self, template_name):
        fn = getattr(self, 'render_' + self.sanitize_template_name(template_name), None)
        assert fn is not None and not isinstance(fn, NanoJekyllContext)
        return fn()
    
    @property
    def first(self):
        return NanoJekyllContext(self._first_(self))
    
    @property
    def size(self):
        return NanoJekyllContext(self._size_(self))
    
    # https://shopify.github.io/liquid/basics/operators/
    # https://jekyllrb.com/docs/liquid/filters/
    
    @staticmethod
    def _first_(xs):
        # https://shopify.github.io/liquid/filters/first/
        return xs[0] if xs else None

    @staticmethod
    def _size_(xs):
        # https://shopify.github.io/liquid/filters/size/
        return len(xs) if xs else 0
    
    
    @staticmethod
    def _date_to_xmlschema_(dt):
        # https://jekyllrb.com/docs/liquid/filters/#date-to-xml-schema
        return str(dt)
    
    @staticmethod
    def _date_(dt, date_format):
        # https://shopify.github.io/liquid/filters/date/
        return str(dt) #.strftime(date_format)

    def _relative_url_(self, url):
        # https://jekyllrb.com/docs/liquid/filters/#relative-url
        base_url = self.ctx.get('site', {}).get('baseurl', '')
        if base_url:
            return os.path.join('/' + base_url.lstrip('/'), url.lstrip('/'))
        return ('.' + url) if url.startswith('/') else url

    def _absolute_url_(self, url):
        # https://jekyllrb.com/docs/liquid/filters/#absolute-url
        site_url = self.ctx.get('site', {}).get('url', '')
        base_url = self.ctx.get('site', {}).get('baseurl', '')
        if site_url:
            return os.path.join(site_url, base_url.lstrip('/'), url.lstrip('/'))
        if base_url:
            return os.path.join('/' + base_url.lstrip('/'), url.lstrip('/'))
        return ('.' + url) if url.startswith('/') else url
    
    @staticmethod
    def _jsonify_(x):
        # https://jekyllrb.com/docs/liquid/filters/#data-to-json
        return json.dumps(x, ensure_ascii = False)

    @staticmethod
    def _default_(s, t):
        # https://shopify.github.io/liquid/filters/default/
        return s or t

    @staticmethod
    def _escape_(s):
        # https://shopify.github.io/liquid/filters/escape/
        # https://github.com/shopify/liquid/blob/77bc56a1c28a707c2b222559ffb0b7b1c5588928/lib/liquid/standardfilters.rb#L99
        return html.escape(str(s)) if s else ''
    
    @staticmethod
    def _xml_escape_(x):
        # https://jekyllrb.com/docs/liquid/filters/#xml-escape
        # https://github.com/jekyll/jekyll/blob/96a4198c27482f061e145953066af501d5e085e2/lib/jekyll/filters.rb#L77
        return html.escape(str(s)) if s else ''

    @staticmethod
    def _append_(xs, item):
        # https://shopify.github.io/liquid/filters/append/
        return str(xs or '') + str(item or '')

    @staticmethod
    def _join_(xs, sep = ''):
        # https://shopify.github.io/liquid/filters/join/
        return sep.join(str(x) for x in xs)

    @staticmethod
    def _remove_(x, y):
        # https://shopify.github.io/liquid/filters/remove/
        return x.replace(y, '')
    
    @staticmethod
    def _strip_(x):
        # https://shopify.github.io/liquid/filters/strip/
        return str(x).strip() if x else ''

    @staticmethod
    def _normalize_whitespace_(x):
        # https://jekyllrb.com/docs/liquid/filters/#normalize-whitespace
        return ' '.join(str(x).split()) if x else ''
    
    @staticmethod
    def _strip_html_(x):
        # https://shopify.github.io/liquid/filters/strip_html/
        return re.sub(r'<[^>]+>', '', str(x)) if x else ''
    
    @staticmethod
    def _capitalize_(x):
        # https://shopify.github.io/liquid/filters/capitalize/
        return ' '.join(word.title() if i == 0 else word.lower() for i, word in enumerate(str(x).split())) if x else ''

    @staticmethod
    def _sort_(x):
        # https://shopify.github.io/liquid/filters/sort/
        return sorted(x)
    
    @staticmethod
    def _reverse_(x):
        # https://shopify.github.io/liquid/filters/reverse/
        return list(reversed(x))
    
    @staticmethod
    def _where_(xs, key, value):
        # https://shopify.github.io/liquid/filters/where/
        return [x for x in xs if x[key] == value]

    @staticmethod
    def _map_(xs, key):
        # https://shopify.github.io/liquid/filters/map/
        return [x[key] for x in xs] if xs else []
    

class NanoJekyllPluginFeedMeta(NanoJekyllTemplate):
    # https://github.com/jekyll/jekyll-feed/blob/master/lib/jekyll-feed/feed.xml
    template_code = '''
<link type="application/atom+xml" rel="alternate" href='{{ site.feed.path | default: "feed.xml" }}' title="{{ site.title }}" />
'''

    #def __str__(self):
    #    indent1, indent2 = ' ' * 4 * self.indent_level, ' ' * 4 * (1 + self.indent_level)
    #    python_source = '\n'.join([
    #        indent1 + 'def render_{template_name}(self):\n'.format(template_name = self.template_name),
    #        indent2 + '''return '<link type="application/atom+xml" rel="alternate" href="{href}" title="{title}" />'.format(href = str(self._relative_url_("feed.xml")), title = str(self.page.title)) '''
    #    ])
    #    return python_source 

class NanoJekyllPluginSeo(NanoJekyllTemplate):
    template_code = '''<!-- NanoJekyll and python does not support question-marks in variable names, so replacing here ? by _ -->

<!-- Begin Jekyll SEO tag v{{ seo_tag.version }} -->
{% if seo_tag.title_ %}
  <title>{{ seo_tag.title }}</title>
{% endif %}

<meta name="generator" content="Jekyll v{{ jekyll.version }}" />

{% if seo_tag.page_title %}
  <meta property="og:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if seo_tag.author.name %}
  <meta name="author" content="{{ seo_tag.author.name }}" />
{% endif %}

<meta property="og:locale" content="{{ seo_tag.page_locale }}" />

{% if seo_tag.description %}
  <meta name="description" content="{{ seo_tag.description }}" />
  <meta property="og:description" content="{{ seo_tag.description }}" />
  <meta property="twitter:description" content="{{ seo_tag.description }}" />
{% endif %}

{% if site.url %}
  <link rel="canonical" href="{{ seo_tag.canonical_url }}" />
  <meta property="og:url" content="{{ seo_tag.canonical_url }}" />
{% endif %}

{% if seo_tag.site_title %}
  <meta property="og:site_name" content="{{ seo_tag.site_title }}" />
{% endif %}

{% if seo_tag.image %}
  <meta property="og:image" content="{{ seo_tag.image.path }}" />
  {% if seo_tag.image.height %}
    <meta property="og:image:height" content="{{ seo_tag.image.height }}" />
  {% endif %}
  {% if seo_tag.image.width %}
    <meta property="og:image:width" content="{{ seo_tag.image.width }}" />
  {% endif %}
  {% if seo_tag.image.alt %}
    <meta property="og:image:alt" content="{{ seo_tag.image.alt }}" />
  {% endif %}
{% endif %}

{% if page.date %}
  <meta property="og:type" content="article" />
  <meta property="article:published_time" content="{{ page.date | date_to_xmlschema }}" />
{% else %}
  <meta property="og:type" content="website" />
{% endif %}

{% if paginator.previous_page %}
  <link rel="prev" href="{{ paginator.previous_page_path | absolute_url }}" />
{% endif %}
{% if paginator.next_page %}
  <link rel="next" href="{{ paginator.next_page_path | absolute_url }}" />
{% endif %}

{% if seo_tag.image %}
  <meta name="twitter:card" content="{{ page.twitter.card | default: site.twitter.card | default: "summary_large_image" }}" />
  <meta property="twitter:image" content="{{ seo_tag.image.path }}" />
{% else %}
  <meta name="twitter:card" content="summary" />
{% endif %}

{% if seo_tag.image.alt %}
  <meta name="twitter:image:alt" content="{{ seo_tag.image.alt }}" />
{% endif %}

{% if seo_tag.page_title %}
  <meta property="twitter:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if site.twitter %}
  <meta name="twitter:site" content="@{{ site.twitter.username | remove:'@' }}" />

  {% if seo_tag.author.twitter %}
    <meta name="twitter:creator" content="@{{ seo_tag.author.twitter | remove:'@' }}" />
  {% endif %}
{% endif %}

{% if site.facebook %}
  {% if site.facebook.admins %}
    <meta property="fb:admins" content="{{ site.facebook.admins }}" />
  {% endif %}

  {% if site.facebook.publisher %}
    <meta property="article:publisher" content="{{ site.facebook.publisher }}" />
  {% endif %}

  {% if site.facebook.app_id %}
    <meta property="fb:app_id" content="{{ site.facebook.app_id }}" />
  {% endif %}
{% endif %}

{% if site.webmaster_verifications %}
  {% if site.webmaster_verifications.google %}
    <meta name="google-site-verification" content="{{ site.webmaster_verifications.google }}" />
  {% endif %}

  {% if site.webmaster_verifications.bing %}
    <meta name="msvalidate.01" content="{{ site.webmaster_verifications.bing }}" />
  {% endif %}

  {% if site.webmaster_verifications.alexa %}
    <meta name="alexaVerifyID" content="{{ site.webmaster_verifications.alexa }}" />
  {% endif %}

  {% if site.webmaster_verifications.yandex %}
    <meta name="yandex-verification" content="{{ site.webmaster_verifications.yandex }}" />
  {% endif %}

  {% if site.webmaster_verifications.baidu %}
    <meta name="baidu-site-verification" content="{{ site.webmaster_verifications.baidu }}" />
  {% endif %}

  {% if site.webmaster_verifications.facebook %}
    <meta name="facebook-domain-verification" content="{{ site.webmaster_verifications.facebook }}" />
  {% endif %}
{% elsif site.google_site_verification %}
  <meta name="google-site-verification" content="{{ site.google_site_verification }}" />
{% endif %}

<script type="application/ld+json">
  {{ seo_tag.json_ld | jsonify }}
</script>

<!-- End Jekyll SEO tag -->
'''
