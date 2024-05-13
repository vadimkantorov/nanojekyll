# https://github.com/aosabook/500lines/tree/master/template-engine as a starting point

import os, sys, re, html, datetime
import inspect

class NanoJekyllTemplate:
    def add_line(self, line = ''):
        self.code.extend([' ' * self.indent_level, line, "\n"])
    
    def indent(self, INDENT_STEP = 4):
        self.indent_level += INDENT_STEP
    
    def dedent(self, INDENT_STEP = 4):
        self.indent_level -= INDENT_STEP
    
    @staticmethod
    def makecls(templates, includes = {}, global_variables = [], return_source = False):
        templates = [NanoJekyllTemplate(template_code, layout_name = layout_name, includes = includes, global_variables = global_variables) for layout_name, template_code in templates.items()]
        
        python_source = 'import os, sys, re, html, datetime\n\n'
        python_source += inspect.getsource(NanoJekyllValue)
        python_source += '\n'.join(''.join(str(c) for c in self.code) for self in templates)
        
        open('render.py', 'w').write(python_source)
        if return_source:
            return python_source
        
        global_namespace = {}
        exec(python_source, global_namespace)
        cls = global_namespace['NanoJekyllValue'] 
        return cls
   
    def __init__(self, template_code, layout_name = '', includes = {}, global_variables = []):
        self.includes = includes
        self.global_variables = global_variables

        self.code = []
        self.indent_level = 0
    
        split_tokens = lambda s: re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", s)
        # https://shopify.github.io/liquid/tags/iteration/#forloop-object

        function_name = NanoJekyllValue.prepare_layout_name(layout_name)
        self.indent()
        self.add_line(f'def render_{function_name}(self):')
        self.indent()
        self.add_line('''nil, false, true, newline, result = None, False, True, "\\n", []''')
        self.add_line("class forloop: index = 1; last = False; first = False; index0 = 0; length = None; rindex = -1;")
        self.add_line("globals().update({k: self.pipify(getattr(self, k)) for k in dir(self) if k != 'ctx' and not k.startswith('__')})")

        if self.global_variables:
            self.add_line(', '.join(self.global_variables) + ' = ' +  ', '.join(f'NanoJekyllValue(self.ctx.get({k!r}))' for k in self.global_variables))

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
                    self.add_line(f'result.append(newline + "```{lang}" + newline)')
                    tokens_i_end = '{%endhighlight%}'
                    i += 1
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        self.add_line('result.append(' + repr(tokens[i]) + ')')
                        i += 1
                    self.add_line('result.append(newline + "```" + newline)')

                elif words[0] == 'if':
                    ops_stack.append('if')
                    self.add_line("if {}:".format(' '.join(words[1:])))
                    self.indent()
                
                elif words[0] == 'else':
                    #ops_stack.append('else')
                    self.dedent()
                    self.add_line("else:".format(' '.join(words[1:])))
                    self.indent()
                
                elif words[0] == 'unless':
                    ops_stack.append('unless')
                    self.add_line("if not( {} ):".format(' '.join(words[1:])))
                    self.indent()
                
                elif words[0] == 'for':
                    # A loop: iterate over expression result.
                    assert len(words) == 4 and words[2] == 'in', f"Don't understand for: {token=}"
                    ops_stack.append('for')
                    self.add_line("for {} in {}:".format(words[1], self._expr_code(words[3]) ) )
                    self.indent()
                
                elif words[0].startswith('end'):
                    # Endsomething.  Pop the ops stack.
                    assert len(words) == 1, f"Don't understand end: {token=}"
                    end_what = words[0][3:]
                    assert ops_stack, f"Too many ends: {token=}"
                    start_what = ops_stack.pop()
                    assert start_what == end_what, f"Mismatched end tag: {start_what=} != {end_what=}"
                    self.dedent()

                elif words[0] == 'include':
                    template_name = words[1]
                    beg = None
                    if len(words) > 2 and '=' in words:
                        beg = ([k for k, w in enumerate(words) if w == '='] or [0])[0] - 1
                        self.add_line('include = NanoJekyllValue(dict(' + ', '.join(words[k] + words[k + 1] + words[k + 2] for k in range(beg, len(words), 3)) + '))')
                    template_name = ' '.join(words[1:beg])

                    if '{{' not in template_name and '}}' not in template_name:
                        frontmatter_include, template_include = self.includes[template_name]
                        tokens = tokens[:i + 1] + split_tokens(template_include) + tokens[i + 1:]
                    else:
                        template_name = ' '.join(words[1:]).replace('{{', '{').replace('}}', '}')
                        template_name = 'f' + repr(template_name)
                        self.add_line('includes = ' + repr(self.includes))
                        self.add_line('include_name = ' + template_name)
                        self.add_line('result.append(includes[include_name][-1])')
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    self.add_line('{} = {}'.format(var_name, expr))

                elif words[0] == 'seo' or words[0] == 'feed_meta':
                    pass
        
                else:
                    assert False, ("Don't understand tag: " + words[0])

            else:
                if token:
                    self.add_line("result.append({})".format(repr(token)))
            
            if e == -3:
                self.add_line("result.append(self.TrimRight())")
            i += 1

        assert not ops_stack, ("Unmatched action tag: " + ops_stack[-1])

        self.add_line('return self.finalize_result(result)')
        self.dedent()
        self.dedent()
        assert self.indent_level == 0
    
    def _expr_code(self, expr):
        is_string_literal = lambda expr: (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'"))
        expr = expr.strip()
        if is_string_literal(expr):
            return expr
        elif "|" in expr:
            pipes = list(map(str.strip, expr.split("|")))
            code = 'NanoJekyllValue(' + self._expr_code(pipes[0]) + ')'
            for func in pipes[1:]:
                func_name, *func_args = func.split(':', maxsplit = 1)
                if not func_args:
                    code = f'{code} | _{func_name}()'
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    code = f'{code} | _{func_name}({func_args})'
                    
        elif "." in expr:
            code = expr
        else:
            code = "%s" % expr
        return code

class NanoJekyllValue:
    # https://shopify.github.io/liquid/basics/operators/
    def __init__(self, ctx = None):
        self.ctx = ctx.ctx if isinstance(ctx, NanoJekyllValue) else ctx
    
    def __or__(self, other):
        return NanoJekyllValue(other[0](self.ctx, *other[1:]))

    def __str__(self):
        return str(self.ctx) if self.ctx else ''

    def __bool__(self):
        return bool(self.ctx)

    def __gt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx > other

    def __ge__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx >= other

    def __lt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx < other

    def __le__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx <= other

    def __eq__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx == other

    def __ne__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllValue) else other
        return self.ctx != other
        
    def __getattr__(self, key):
        if isinstance(self.ctx, dict):
            if key in self.ctx:
                return NanoJekyllValue(self.ctx[key])
        return NanoJekyllValue(getattr(self.ctx, key, None))
    
    def __getitem__(self, index):
        if isinstance(self.ctx, (list, str)):
            return NanoJekyllValue(self.ctx[index])
        if isinstance(self.ctx, dict):
            return NanoJekyllValue(self.ctx.get(index))
        return NanoJekyllValue(None)

    def __len__(self):
        return len(self.ctx) if isinstance(self.ctx, (list, dict, str)) else None

    def __iter__(self):
        yield from (map(NanoJekyllValue, self.ctx) if self.ctx else [])

    @staticmethod
    def pipify(f):
        return (lambda *args: (f, *args))
    
    # https://shopify.github.io/liquid/basics/operators/
    # https://jekyllrb.com/docs/liquid/filters/

    @staticmethod
    def _relative_url(url):
        # https://jekyllrb.com/docs/liquid/filters/
        return ('.' + url) if url.startswith('/') else url

    @staticmethod
    def _absolute_url(url):
        # https://jekyllrb.com/docs/liquid/filters/
        return url
    
    @staticmethod
    def _date_to_xmlschema(dt):
        pass
    
    @staticmethod
    def _date(dt, date_format):
        # https://shopify.github.io/liquid/filters/date/
        return dt #.strftime(date_format)

    @staticmethod
    def _escape(s):
        # https://shopify.github.io/liquid/filters/escape/
        return html.escape(str(s)) if s else ''
    
    @staticmethod
    def _default(s, t):
        # https://shopify.github.io/liquid/filters/default/
        return s or t

    @staticmethod
    def _where(xs, key, value):
        # https://shopify.github.io/liquid/filters/where/
        return [x for x in xs if x[key] == value]

    @staticmethod
    def _map(xs, key):
        # https://shopify.github.io/liquid/filters/map/
        return [x[key] for x in xs] if xs else []
    
    @staticmethod
    def _append(xs, item):
        # https://shopify.github.io/liquid/filters/append/
        return str(xs or '') + str(item or '')

    @staticmethod
    def _first(xs):
        # https://shopify.github.io/liquid/filters/first/
        return xs[0] if xs else None

    @staticmethod
    def _size(xs):
        # https://shopify.github.io/liquid/filters/size/
        return len(xs)

    @staticmethod
    def _join(xs, sep):
        # https://shopify.github.io/liquid/filters/join/
        return sep.join(str(x) for x in xs)

    @staticmethod
    def _remove(x, y):
        return x.replace(y, '')

    @staticmethod
    def _jsonify(x):
        return json.dumps(x, ensure_ascii = False)

    @staticmethod
    def _xml_escape(x):
        return x

    @staticmethod
    def _capitalize(x):
        return x

    @staticmethod
    def _smartify(x):
        return x

    @staticmethod
    def _where_exp(x, y):
        return x

    @staticmethod
    def _sort(x):
        return sorted(x)
    
    @staticmethod
    def _reverse(x):
        return list(reversed(x))

    @staticmethod
    def _strip(x):
        return x

    @staticmethod
    def _strip_html(x):
        return x

    @staticmethod
    def _normalize_whitespace(x):
        return x

    @property
    def size(self):
        return NanoJekyllValue(len(self) if self else 0)
        
    class TrimLeft(str): pass
    class TrimRight(str): pass
    @staticmethod
    def finalize_result(result):
        return ''.join(result)
    
    @staticmethod
    def prepare_layout_name(layout_name):
        return os.path.splitext(layout_name)[0].translate({ord('/') : '_', ord('-'): '_', ord('.') : '_'})

    def render(self, layout_name):
        fn = getattr(self, 'render_' + self.prepare_layout_name(layout_name), None)
        assert fn is not None and not isinstance(fn, NanoJekyllValue)
        return fn()
