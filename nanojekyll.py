import os, sys, re, html, json, math, datetime, itertools, urllib.parse
import inspect

def yaml_loads(content, convert_bool = True, convert_int = True, convert_dict = True): # from https://gist.github.com/vadimkantorov/b26eda3645edb13feaa62b874a3e7f6f
    def procval(val):
        read_until = lambda tail, chars: ([(tail[:i], tail[i+1:]) for i, c in enumerate(tail) if c in chars] or [(tail, '')])[0]

        val = val.strip()
        is_quoted_string = len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'"))
        if is_quoted_string:
            return val[1:-1]
        else:
            val = val.split('#', maxsplit = 1)[0].strip()
            is_int = val.isdigit()
            is_bool = val.lower() in ['true', 'false']
            is_dict = len(val) >= 2 and (val[0] == '{' and val[-1] == '}')
            if is_int and convert_int:
                return int(val) if convert_int else val
            elif is_bool and convert_bool:
                return dict(true = True, false = False)[val.lower()] if convert_int else val
            elif is_dict and convert_dict:
                res = {}
                tail = val
                head, tail = read_until(tail, '{')
                while tail:
                    key, tail = read_until(tail, ':')
                    val, tail = read_until(tail, ',}')
                    res[key.strip()] = procval(val.strip())
                return res
        return val

    lines = content.strip().splitlines()

    res = {}
    keyprev = ''
    indentprev = 0
    dictprev = {}
    is_multiline = False
    stack = {0: ({None: res}, None)}
    begin_multiline_indent = 0

    for line in lines:
        line_lstrip = line.lstrip()
        line_strip = line.strip()
        indent = len(line) - len(line_lstrip)
        splitted_colon = line.split(':', maxsplit = 1)
        key, val = (splitted_colon[0].strip(), splitted_colon[1].strip()) if len(splitted_colon) > 1 else ('', line_strip)
        is_list_item = line_lstrip.startswith('- ') or line_lstrip.rstrip() == '-'
        list_val = line_strip.split('-', maxsplit = 1)[-1].lstrip() if is_list_item else ''
        is_comment = not line_strip or line_lstrip.startswith('#')
        is_dedent = indent < indentprev
        begin_multiline = val in ['>', '|', '|>']
        is_record = len(list_val) >= 2 and list_val[0] == '{' and list_val[-1] == '}'

        if is_multiline and begin_multiline_indent and indent < begin_multiline_indent:
            is_multiline = False
            begin_multiline_indent = 0

        if not is_multiline:
            if is_list_item and indent in stack and isinstance(stack[indent][0][stack[indent][1]], dict):
                indent += 2
            if indent not in stack:
                stack[indent] = (stack[indentprev][0][stack[indentprev][1]], keyprev) if keyprev is not None else ({None: dictprev}, None)
            curdict, curkey = stack[indent]

        if is_comment:
            continue

        elif is_list_item:
            curdict[curkey] = curdict[curkey] or []
            if list_val and (not key) or is_record:
                curdict[curkey].append(procval(list_val))
            else:
                dictprev = {key.removeprefix('- ') : procval(list_val)} if list_val else {}
                curdict[curkey].append(dictprev)
                key = None

        elif begin_multiline:
            curdict[curkey][key] = ''
            curdict, curkey = curdict[curkey], key
            is_multiline = True

        elif is_multiline:
            curdict[curkey] += ('\n' + val) if curdict[curkey] else val
            begin_multiline_indent = min(indent, begin_multiline_indent) if begin_multiline_indent else indent

        elif key and not val:
            curdict[curkey][key] = dictprev = {}

        else:
            curdict[curkey][key] = procval(val)

        if is_dedent:
            stack = {i : v for i, v in stack.items() if i <= indent}

        indentprev = indent
        keyprev = key

    return res

class NanoJekyllTemplate:
    @staticmethod
    def read_template(path, front_matter_sep = '---\n', parse_yaml = True):
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
        return front_matter if not parse_yaml else yaml_loads(front_matter), template

    @staticmethod
    def codegen(templates, includes = {}, global_variables = [], plugins = {}, newline = '\n'):
        indent_level = 1

        python_source  = 'import os, sys, re, html, json, math, datetime, itertools, urllib.parse' + newline
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
        self.add_line('nil, empty, false, true, NanoJekyllResult, cycle_cache = None, None, False, True, [], {}')
        self.add_line('class forloop: index0, index, rindex, rindex0, first, last, length = -1, -1, -1, -1, False, False, -1')

        filters_names = [k for k in dir(NanoJekyllContext) if (k.startswith('_') and not k.startswith('__')) and (k.endswith('_') and not k.endswith('__'))]
        self.add_line('( ' + ', '.join(filters_names        ) +' ) = ( ' + ', '.join(f'self.pipify(self.{k})' for k in filters_names) + ' )')
        self.add_line('( ' + ', '.join(self.global_variables) +' ) = ( ' + ', '.join(NanoJekyllContext.__name__ + f'(self.ctx.get({k!r}))' for k in self.global_variables) + ' )')

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
                self.add_line("NanoJekyllResult.append(self.NanoJekyllTrimLeft())")

            if token.startswith('{{'):
                expr = self._expr_code(token_inner)
                self.add_line(f"NanoJekyllResult.append(str({expr}))")

            elif token.startswith('{%'):
                if words[0] == '-':
                    del words[0]
                if words[-1] == '-':
                    del words[-1]

                if words[0] == 'comment':
                    tokens_i_end = tokens[i].replace(' ', '').replace('comment', 'endcomment')
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        i += 1
                
                elif words[0] == 'cycle':
                    line_number = self.add_line('#')
                    self.add_line(f'NanoJekyllResult.append(self.cycle(line_number = {line_number}, cycle_cache = cycle_cache, vals = ( ' + ' '.join(words[1:]) + ') ))')
    
                elif words[0] == 'highlight':
                    lang = ''.join(words[1:])
                    self.add_line(f'NanoJekyllResult.append("\\n```{lang}\\n")')
                    tokens_i_end = '{%endhighlight%}'
                    i += 1
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        self.add_line('NanoJekyllResult.append(' + repr(tokens[i]) + ')')
                        i += 1
                    self.add_line('NanoJekyllResult.append("\\n```\\n")')
                
                elif words[0] == 'unless':
                    ops_stack.append('unless')
                    if 'contains' in words:
                        assert len(words) == 4 and words[2] == 'contains'
                        words = [words[0], words[3], 'in', words[1]]
                    self.add_line("if not( {} ):".format(' '.join(words[1:])))
                    self.indent_level += 1

                elif words[0] == 'if':
                    ops_stack.append('if')
                    if 'contains' in words:
                        assert len(words) == 4 and words[2] == 'contains'
                        words = [words[0], words[3], 'in', words[1]]
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
                
                elif words[0] == 'for':
                    # https://shopify.dev/docs/api/liquid/objects/forloop
                    assert len(words) in [4, 6] and words[2] == 'in', f'Dont understand for: {token=}'

                    ops_stack.append('for')
                    forloop_cnt = self.add_line('#')
                    self.add_line('forloop_{} = list({})'.format(forloop_cnt, self._expr_code(words[3])))
                    if len(words) == 6 and words[4] == 'limit:':
                        self.add_line('forloop_{0} = forloop_{0}[:(int({1}) if {1} else None)]'.format(forloop_cnt, self._expr_code(words[5])))
                    self.add_line('for forloop.index0, {} in enumerate(forloop_{}):'.format(words[1], forloop_cnt))
                    self.indent_level += 1
                    self.add_line('forloop.index, forloop.rindex, forloop.rindex0, forloop.first, forloop.last, forloop.length = forloop.index0 + 1, len(forloop_{0}) - forloop.index0, len(forloop_{0}) - forloop.index0 - 1, forloop.index0 == 0, forloop.index0 == len(forloop_{0}) - 1, len(forloop_{0})'.format(forloop_cnt))
                
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
                        self.add_line('NanoJekyllResult.append(self.includes[include_name][-1])')
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    self.add_line('{} = {}'.format(var_name, expr))

                elif words[0] in plugins: 
                    template_name = words[0]
                    self.add_line(f'assert bool(self.render_plugin_{template_name}); tmp = self.render_plugin_{template_name}(); (NanoJekyllResult.extend if isinstance(tmp, list) else NanoJekyllResult.append)(tmp)')
                else:
                    assert False, ('Dont understand tag: ' + words[0])

            else:
                if token:
                    self.add_line("NanoJekyllResult.append({})".format(repr(token)))
            
            if e == -3:
                self.add_line('NanoJekyllResult.append(self.NanoJekyllTrimRight())')
            i += 1

        assert not ops_stack, ('Unmatched action tag: ' + ops_stack[-1])

        self.add_line('return self.NanoJekyllResultFinalize(NanoJekyllResult)')
    
    def _expr_code(self, expr):
        is_string_literal = lambda expr: (expr.startswith('"') and expr.endswith('"') and expr[1:-1].count('"') == 0) or (expr.startswith("'") and expr.endswith("'") and expr[1:-1].count("'") == 0)
        expr = expr.strip()

        if is_string_literal(expr):
             code = expr

        elif '|' in expr:
            pipes = list(map(str.strip, expr.split('|')))
            i = 0
            while i < len(pipes):
                if pipes[i].count('"') % 2 == 1:
                    pipes = pipes[:i] + [pipes[i] + ' | ' + pipes[i + 1]] + pipes[i + 2:]
                    i += 1
                i += 1

            code = NanoJekyllContext.__name__+ '(' + self._expr_code(pipes[0]) + ')' if is_string_literal(pipes[0]) else self._expr_code(pipes[0])
            for func in pipes[1:]:
                func_name, *func_args = func.split(':', maxsplit = 1)
                
                if not func_args:
                    code = f'{code} | _{func_name}_()'
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    code = f'{code} | _{func_name}_({func_args})'
                    
        else:
            code = expr

        return code

    def __str__(self):
        return ''.join(map(str, self.code)) 

    def add_line(self, line = ''):
        self.code.extend([' ' * 4 * self.indent_level, line, "\n"])
        return len(self.code)

class NanoJekyllContext:
    class NanoJekyllTrimLeft(str): pass
    class NanoJekyllTrimRight(str): pass
    
    def __init__(self, ctx = None):
        # https://shopify.github.io/liquid/basics/operators/
        # https://shopify.dev/docs/api/liquid/filters/escape
        # https://jekyllrb.com/docs/liquid/filters/
    
        self.ctx = ctx.ctx if isinstance(ctx, NanoJekyllContext) else ctx
    
    def __or__(self, other):
        return NanoJekyllContext(other[0](self.ctx, *other[1:]))

    def __str__(self):
        return str(self.ctx) if self.ctx else ''

    def __bool__(self):
        return bool(self.ctx)

    def __int__(self):
        return int(self.ctx)

    def __abs__(self):
        return abs(self.ctx) if isinstance(self.ctx, int | float) else 0 if (not self.ctx or not isinstance(self.ctx, str | int | float)) else abs(int(self.ctx)) if (self.ctx and isinstance(self.ctx, str) and self.ctx[1:].isigit() and (self.ctx[0].isdigit() or self.ctx[0] == '-')) else abs(float(self.ctx))
    
    def __round__(self):
        return round(float(self.ctx) if self.ctx and isinstance(self.ctx, str | int | float) else 0)
    
    def __floor__(self):
        return math.floor(float(self.ctx) if self.ctx and isinstance(self.ctx, str | int | float) else 0)
    
    def __ceil__(self):
        return math.ceil(float(self.ctx) if self.ctx and isinstance(self.ctx, str | int | float) else 0)

    def __mul__(self, other):
        return NanoJekyllContext(self.ctx * other)
    
    def __truediv__(self, other):
        return NanoJekyllContext((self.ctx or 0) / other)
    
    def __floordiv__(self, other):
        return NanoJekyllContext(math.floor((self.ctx or 0) // other))
    
    def __mod__(self, other):
        return NanoJekyllContext((self.ctx or 0) % other)

    def __gt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx > other

    def __ge__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx >= other

    def __lt__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return (self.ctx < other) if self.ctx and other else True if self.ctx else False

    def __le__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx <= other

    def __eq__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx == other

    def __ne__(self, other):
        other = other.ctx if isinstance(other, NanoJekyllContext) else other
        return self.ctx != other
        
    def __getattr__(self, other):
        if isinstance(self.ctx, dict):
            if other in self.ctx:
                return NanoJekyllContext(self.ctx[other])
        return NanoJekyllContext(getattr(self.ctx, other, None))
    
    def __getitem__(self, other):
        if not self.ctx:
            return NanoJekyllContext(None)
        if isinstance(self.ctx, (list, tuple, str)):
            return NanoJekyllContext(self.ctx[int(other)])
        if isinstance(self.ctx, dict):
            return NanoJekyllContext(self.ctx.get(str(other)))
        return NanoJekyllContext(None)

    def __len__(self):
        return len(self.ctx) if isinstance(self.ctx, (list, dict, str)) else None

    def __iter__(self):
        yield from (map(NanoJekyllContext, self.ctx) if self.ctx else [])

    @staticmethod
    def pipify(f):
        return (lambda *args: (f, *args))

    @staticmethod
    def cycle(line_number, cycle_cache = {}, vals = ()):
        if not vals:
            return ''
        if line_number not in cycle_cache:
            cycle_cache[line_number] = -1
        cycle_cache[line_number] = (cycle_cache[line_number] + 1) % len(vals)
        return str(vals[cycle_cache[line_number]])
        
    @staticmethod
    def NanoJekyllResultFinalize(result):
        # https://shopify.github.io/liquid/basics/whitespace/
        res = ''
        trimming = False
        for s in result:
            if isinstance(s, NanoJekyllContext.NanoJekyllTrimLeft):
                res = res.rstrip()
            elif isinstance(s, NanoJekyllContext.NanoJekyllTrimRight):
                trimming = True
            else:
                if trimming:
                    s = s.lstrip()
                if s:
                    res += s
                    trimming = False
        return res
    
    @staticmethod
    def sanitize_template_name(template_name, translate = {ord('/') : '_', ord('-'): '_', ord('.') : '_'}):
        return os.path.splitext(os.path.basename(template_name))[0].translate(translate)

    def render(self, template_name, is_plugin = False):
        fn = getattr(self, ('render_' if not is_plugin else 'render_plugin_') + self.sanitize_template_name(template_name), None)
        assert fn is not None and not isinstance(fn, NanoJekyllContext)
        return fn()
    
    @property
    def first(self):
        return NanoJekyllContext(self._first_(self))
    
    @property
    def last(self):
        return NanoJekyllContext(self._last_(self))
    
    @property
    def size(self):
        return NanoJekyllContext(self._size_(self))
    
    
    @staticmethod
    def _first_(xs):
        # https://shopify.github.io/liquid/filters/first/
        return xs[0] if xs else None
    
    @staticmethod
    def _last_(xs):
        # https://shopify.github.io/liquid/filters/last/
        return xs[-1] if xs else None

    @staticmethod
    def _size_(xs):
        # https://shopify.github.io/liquid/filters/size/
        return len(xs) if xs else 0
    
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
    def _escape_once_(s):
        # https://shopify.github.io/liquid/filters/escape_once/
        return html.escape(html.unescape(str(s))) if s else ''
    
    @staticmethod
    def _url_encode_(s):
        # https://shopify.github.io/liquid/filters/url_encode/
        return urllib.parse.quote_plus(str(s)) if s else ''
    
    @staticmethod
    def _url_decode_(s):
        # https://shopify.github.io/liquid/filters/url_decode/
        return urllib.parse.unquote_plus(str(s)) if s else ''
    
    @staticmethod
    def _append_(xs, x):
        # https://shopify.github.io/liquid/filters/append/
        return str(xs or '') + str(x or '')
    
    @staticmethod
    def _prepend_(xs, x):
        # https://shopify.github.io/liquid/filters/prepend/
        return str(x or '') or str(xs or '')

    @staticmethod
    def _truncate_(x, y, z = '...'):
        # https://shopify.github.io/liquid/filters/truncate/
        return (str(x) if len(x) <= y - len(z) else str(x)[:y - len(z)].rstrip() + z) if x else ''
    
    @staticmethod
    def _truncatewords_(x, y, z = '...'):
        # https://shopify.github.io/liquid/filters/truncatewords/
        return (str(x) if len(str(x).split()) <= y - len(z) else ' '.join(str(x).split()[:y - len(z)]).rstrip() + z) if x else ''

    @staticmethod
    def _join_(xs, sep = ''):
        # https://shopify.github.io/liquid/filters/join/
        return sep.join(str(x) for x in xs) if xs else ''

    @staticmethod
    def _split_(xs, sep = ''):
        # https://shopify.github.io/liquid/filters/split/
        return xs.split(sep) if xs and sep in xs else []

    @staticmethod
    def _concat_(xs, ys = []):
        # https://shopify.github.io/liquid/filters/concat/
        return (list(xs) if xs else []) + list(ys)

    @staticmethod
    def _compact_(xs):
        # https://shopify.github.io/liquid/filters/compact/
        return list(filter(bool, xs)) if xs else []
    
    @staticmethod
    def _uniq_(xs):
        # https://shopify.github.io/liquid/filters/uniq/
        return list({x : None for x in xs}.keys()) if xs else []
    
    @staticmethod
    def _abs_(x):
        # https://shopify.github.io/liquid/filters/abs/
        return abs(x)
    
    @staticmethod
    def _at_least_(x):
        # https://shopify.github.io/liquid/filters/at_least/
        return min(self.ctx, x) if isinstance(self.ctx, int | float) else float(x or 0)
    
    @staticmethod
    def _at_most_(x):
        # https://shopify.github.io/liquid/filters/at_most/
        return max(self.ctx, x) if isinstance(self.ctx, int | float) else float(x or 0)

    @staticmethod
    def _round_(x):
        # https://shopify.github.io/liquid/filters/round/
        return round(x)
    
    @staticmethod
    def _ceil_(x):
        # https://shopify.github.io/liquid/filters/ceil/
        return math.ceil(x)
    
    @staticmethod
    def _floor_(x):
        # https://shopify.github.io/liquid/filters/floor/
        return math.floor(x)
    
    @staticmethod
    def _slice_(xs, begin, cnt = 1):
        # https://shopify.github.io/liquid/filters/slice/
        assert int(begin) >= 0
        if not xs:
            return xs
        if int(begin) >= 0:
            return xs[int(begin):(int(begin) + int(cnt))]
        else:
            return xs[int(begin) - int(cnt) : (int(begin) + 1 if int(begin) != -1 else None)]
    
    @staticmethod
    def _minus_(xs, sep = 0):
        # https://shopify.github.io/liquid/filters/minus/
        return (xs if xs else 0) - sep

    @staticmethod
    def _plus_(xs, sep = 0):
        # https://shopify.github.io/liquid/filters/minus/
        return (xs if xs else 0) + sep

    @staticmethod
    def _remove_(x, y):
        # https://shopify.github.io/liquid/filters/remove/
        return str(x).replace(y, '') if x else ''
    
    @staticmethod
    def _remove_first_(x, y):
        # https://shopify.github.io/liquid/filters/replace_first/
        x, y = str(x or ''), str(y or '')
        idx = x.index(y)
        return (x[:idx] + x[idx + len(y):] if idx >= 0 else x) if x else ''
    
    @staticmethod
    def _replace_(x, y, z = ''):
        # https://shopify.github.io/liquid/filters/replace/
        return str(x).replace(y or '', z or '') if x else ''
    
    @staticmethod
    def _replace_first_(x, y, z = ''):
        # https://shopify.github.io/liquid/filters/replace_first/
        x, y, z = str(x or ''), str(y or ''), str(z or '')
        idx = x.index(y)
        return (x[:idx] + z + x[idx + len(y):] if idx >= 0 else x) if x else ''
    
    @staticmethod
    def _strip_(x):
        # https://shopify.github.io/liquid/filters/strip/
        return str(x).strip() if x else ''
    
    @staticmethod
    def _lstrip_(x):
        # https://shopify.github.io/liquid/filters/lstrip/
        return str(x).lstrip() if x else ''

    @staticmethod
    def _rstrip_(x):
        # https://shopify.github.io/liquid/filters/rstrip/
        return str(x).rstrip() if x else ''

    @staticmethod
    def _newline_to_br_(x):
        # https://shopify.github.io/liquid/filters/newline_to_br/
        return str(x).replace('\n', '<br />\n') if x else ''

    @staticmethod
    def _strip_html_(x):
        # https://shopify.github.io/liquid/filters/strip_html/
        return re.sub(r'<[^>]+>', '', str(x)) if x else ''
    
    @staticmethod
    def _strip_newlines_(x):
        # https://shopify.github.io/liquid/filters/strip_newlines/
        return str(x).replace('\r', '').replace('\n', '') if x else ''
    
    @staticmethod
    def _capitalize_(x):
        # https://shopify.github.io/liquid/filters/capitalize/
        return ' '.join(word.title() if i == 0 else word.lower() for i, word in enumerate(str(x).split())) if x else ''

    @staticmethod
    def _sort_(xs, key = ''):
        # https://shopify.github.io/liquid/filters/sort/
        expr = eval(f'lambda item: item.{key}') if key else None
        return sorted([NanoJekyllContext(x) for x in xs], key = expr) if xs else []
    
    @staticmethod
    def _sort_natural_(xs, key = ''):
        # https://shopify.github.io/liquid/filters/sort_natural/
        expr = eval(f'lambda item, lower = (lambda v: v.lower() if isinstance(v, str) else v): lower(item.{key})') if key else (lambda v: v.lower() if isinstance(v, str) else v)
        return sorted([NanoJekyllContext(x) for x in xs], key = expr) if xs else []
    
    @staticmethod
    def _reverse_(x):
        # https://shopify.github.io/liquid/filters/reverse/
        return list(reversed(x)) if x else ''
    
    @staticmethod
    def _where_(xs, key, value):
        # https://shopify.github.io/liquid/filters/where/
        return [x for x in xs if x.get(key, None) == value] if xs else []
    
    @staticmethod
    def _sum_(xs, key = ''):
        # https://shopify.github.io/liquid/filters/sum/
        return sum(x if not key else x.get(key, 0) for x in xs) if xs else 0
    
    @staticmethod
    def _times_(x, y = 1):
        # https://shopify.github.io/liquid/filters/times/
        return (x * y) if x else 0

    @staticmethod
    def _divided_by_(x, y = 1):
        # https://shopify.github.io/liquid/filters/divided_by/
        return (x // y) if isinstance(y, int) else (x / y) if isinstance(y, float) else 0
    
    @staticmethod
    def _modulo_(x, y = 1):
        # https://shopify.github.io/liquid/filters/modulo/
        return (x % y) if x and y else 0

    @staticmethod
    def _map_(xs, key):
        # https://shopify.github.io/liquid/filters/map/
        return [x[key] for x in xs] if xs else []
    
    @staticmethod
    def _downcase_(x):
        # https://shopify.github.io/liquid/filters/downcase/
        return str(x).lower() if x else ''
    
    @staticmethod
    def _upcase_(x):
        # https://shopify.github.io/liquid/filters/upcase/
        return str(x).upper() if x else ''
    
    @staticmethod
    def _date_(dt, date_format):
        # https://shopify.github.io/liquid/filters/date/
        #%Y
        #%m
        #%d 
        #%H
        #%M
        #%b
        #%y
        #Symbol	Meaning	Example
        #%a	Abbreviated weekday name (Sun, Mon, ...)	Sun
        #%A	Full weekday name (Sunday, Monday, ...)	Sunday
        #%b	Abbreviated month name (Jan, Feb, ...)	Jan
        #%B	Full month name (January, February, ...)	January
        #%c	Date and time representation	Mon Jan 01 00:00:00 2023
        #%C	Century number (year/100) as a 2-digit integer	20
        #%d	Day of the month as a 2-digit integer	01
        #%D	Date in the format %m/%d/%y	01/01/23
        #%e	Day of the month as a decimal number, padded with space	1
        #%F	ISO 8601 date format (yyyy-mm-dd)	2023-01-01
        #%H	Hour of the day (00..23) as a 2-digit integer	00
        #%I	Hour of the day (01..12) as a 2-digit integer	12
        #%j	Day of the year as a 3-digit integer	001
        #%k	Hour of the day (0..23) as a decimal number, padded	0
        #%l	Hour of the day (1..12) as a decimal number, padded	12
        #%m	Month of the year as a 2-digit integer	01
        #%M	Minute of the hour as a 2-digit integer	00
        #%n	Newline
        #%p	AM or PM	AM
        #%P	am or pm	am
        #%r	Time in AM/PM format	12:00:00 AM
        #%R	Time in 24-hour format	00:00
        #%s	Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)	1577836800
        #%S	Second of the minute as a 2-digit integer	00
        #%t	Tab
        #%T	Time in 24-hour format with seconds	00:00:00
        #%u	Day of the week as a decimal, Monday being 1	1
        #%U	Week number of the year (Sunday as the first day)	00
        #%V	Week number of the year (ISO week numbering)	01
        #%w	Day of the week as a decimal, Sunday being 0	0
        #%W	Week number of the year (Monday as the first day)	00
        #%x	Preferred representation of date	01/01/23
        #%X	Preferred representation of time	00:00:00
        #%y	Year without century as a 2-digit integer	23
        #%Y	Year with century as a 4-digit integer	2023
        #%z	Time zone offset from UTC in the form +HHMM or -HHMM	+0000
        #%Z	Time zone name or abbreviation	UTC
        #%%	A literal '%' character	%
        return str(dt) if dt else '' #.strftime(date_format)

    
    @staticmethod
    def _date_to_xmlschema_(dt):
        # https://jekyllrb.com/docs/liquid/filters/#date-to-xml-schema
        # https://github.com/jekyll/jekyll/blob/60a9cd73569552b858e807cbd3c0e23455023cbc/lib/jekyll/filters/date_filters.rb#L49
        
        #Date to XML Schema
        #Convert a Date into XML Schema (ISO 8601) format.
        #{{ site.time | date_to_xmlschema }}
        #2008-11-07T13:07:54-08:00
        
        return dt.isoformat(timespec='seconds') if dt else ''
    
    
    @staticmethod
    def _date_to_rfc822_(dt):
        # https://jekyllrb.com/docs/liquid/filters/#date-to-rfc-822-format
        # https://github.com/jekyll/jekyll/blob/60a9cd73569552b858e807cbd3c0e23455023cbc/lib/jekyll/filters/date_filters.rb#L65
        
        #Date to RFC-822 Format
        #Convert a Date into the RFC-822 format used for RSS feeds.
        #{{ site.time | date_to_rfc822 }}
        #Mon, 07 Nov 2008 13:07:54 -0800

        return datetime.datetime.strftime(dt, '%a, %d %b %Y %H:%M:%S %z') if dt else ''
    
    @staticmethod
    def _date_to_string_(dt, y = 'ordinal', z = 'US'):
        # https://jekyllrb.com/docs/liquid/filters/#date-to-string
        # https://github.com/jekyll/jekyll/blob/60a9cd73569552b858e807cbd3c0e23455023cbc/lib/jekyll/filters/date_filters.rb#L18
        
        #Date to String
        #Convert a date to short format.
        #{{ site.time | date_to_string }}
        #07 Nov 2008
        #Date to String in ordinal US style
        #Format a date to ordinal, US, short format. 3.8.0
        #{{ site.time | date_to_string: "ordinal", "US" }}
        #Nov 7th, 2008
        
        return datetime.datetime.strftime(dt, '%d %b %Y') if dt else ''
    
    @staticmethod
    def _date_to_long_string_(dt, y = 'ordinal', z = 'US'):
        # https://jekyllrb.com/docs/liquid/filters/#date-to-long-string
        # https://github.com/jekyll/jekyll/blob/60a9cd73569552b858e807cbd3c0e23455023cbc/lib/jekyll/filters/date_filters.rb#L33
        
        #Date to Long String
        #Format a date to long format.
        #{{ site.time | date_to_long_string }}
        #07 November 2008
        #Date to Long String in ordinal UK style
        #Format a date to ordinal, UK, long format. 3.8.0
        #{{ site.time | date_to_long_string: "ordinal" }}
        #7th November 2008
        
        return str(dt) if dt else ''
    
    @staticmethod
    def _slugify_(s, mode = '', space = '_', lower = True):
        # https://jekyllrb.com/docs/liquid/filters/#slugify
        # regex from https://github.com/Flet/github-slugger, see https://github.com/github/cmark-gfm/issues/361
        #regex_bad_chars = r'[\0-\x1F!-,\.\/:-@\[-\^`\{-\xA9\xAB-\xB4\xB6-\xB9\xBB-\xBF\xD7\xF7\u02C2-\u02C5\u02D2-\u02DF\u02E5-\u02EB\u02ED\u02EF-\u02FF\u0375\u0378\u0379\u037E\u0380-\u0385\u0387\u038B\u038D\u03A2\u03F6\u0482\u0530\u0557\u0558\u055A-\u055F\u0589-\u0590\u05BE\u05C0\u05C3\u05C6\u05C8-\u05CF\u05EB-\u05EE\u05F3-\u060F\u061B-\u061F\u066A-\u066D\u06D4\u06DD\u06DE\u06E9\u06FD\u06FE\u0700-\u070F\u074B\u074C\u07B2-\u07BF\u07F6-\u07F9\u07FB\u07FC\u07FE\u07FF\u082E-\u083F\u085C-\u085F\u086B-\u089F\u08B5\u08C8-\u08D2\u08E2\u0964\u0965\u0970\u0984\u098D\u098E\u0991\u0992\u09A9\u09B1\u09B3-\u09B5\u09BA\u09BB\u09C5\u09C6\u09C9\u09CA\u09CF-\u09D6\u09D8-\u09DB\u09DE\u09E4\u09E5\u09F2-\u09FB\u09FD\u09FF\u0A00\u0A04\u0A0B-\u0A0E\u0A11\u0A12\u0A29\u0A31\u0A34\u0A37\u0A3A\u0A3B\u0A3D\u0A43-\u0A46\u0A49\u0A4A\u0A4E-\u0A50\u0A52-\u0A58\u0A5D\u0A5F-\u0A65\u0A76-\u0A80\u0A84\u0A8E\u0A92\u0AA9\u0AB1\u0AB4\u0ABA\u0ABB\u0AC6\u0ACA\u0ACE\u0ACF\u0AD1-\u0ADF\u0AE4\u0AE5\u0AF0-\u0AF8\u0B00\u0B04\u0B0D\u0B0E\u0B11\u0B12\u0B29\u0B31\u0B34\u0B3A\u0B3B\u0B45\u0B46\u0B49\u0B4A\u0B4E-\u0B54\u0B58-\u0B5B\u0B5E\u0B64\u0B65\u0B70\u0B72-\u0B81\u0B84\u0B8B-\u0B8D\u0B91\u0B96-\u0B98\u0B9B\u0B9D\u0BA0-\u0BA2\u0BA5-\u0BA7\u0BAB-\u0BAD\u0BBA-\u0BBD\u0BC3-\u0BC5\u0BC9\u0BCE\u0BCF\u0BD1-\u0BD6\u0BD8-\u0BE5\u0BF0-\u0BFF\u0C0D\u0C11\u0C29\u0C3A-\u0C3C\u0C45\u0C49\u0C4E-\u0C54\u0C57\u0C5B-\u0C5F\u0C64\u0C65\u0C70-\u0C7F\u0C84\u0C8D\u0C91\u0CA9\u0CB4\u0CBA\u0CBB\u0CC5\u0CC9\u0CCE-\u0CD4\u0CD7-\u0CDD\u0CDF\u0CE4\u0CE5\u0CF0\u0CF3-\u0CFF\u0D0D\u0D11\u0D45\u0D49\u0D4F-\u0D53\u0D58-\u0D5E\u0D64\u0D65\u0D70-\u0D79\u0D80\u0D84\u0D97-\u0D99\u0DB2\u0DBC\u0DBE\u0DBF\u0DC7-\u0DC9\u0DCB-\u0DCE\u0DD5\u0DD7\u0DE0-\u0DE5\u0DF0\u0DF1\u0DF4-\u0E00\u0E3B-\u0E3F\u0E4F\u0E5A-\u0E80\u0E83\u0E85\u0E8B\u0EA4\u0EA6\u0EBE\u0EBF\u0EC5\u0EC7\u0ECE\u0ECF\u0EDA\u0EDB\u0EE0-\u0EFF\u0F01-\u0F17\u0F1A-\u0F1F\u0F2A-\u0F34\u0F36\u0F38\u0F3A-\u0F3D\u0F48\u0F6D-\u0F70\u0F85\u0F98\u0FBD-\u0FC5\u0FC7-\u0FFF\u104A-\u104F\u109E\u109F\u10C6\u10C8-\u10CC\u10CE\u10CF\u10FB\u1249\u124E\u124F\u1257\u1259\u125E\u125F\u1289\u128E\u128F\u12B1\u12B6\u12B7\u12BF\u12C1\u12C6\u12C7\u12D7\u1311\u1316\u1317\u135B\u135C\u1360-\u137F\u1390-\u139F\u13F6\u13F7\u13FE-\u1400\u166D\u166E\u1680\u169B-\u169F\u16EB-\u16ED\u16F9-\u16FF\u170D\u1715-\u171F\u1735-\u173F\u1754-\u175F\u176D\u1771\u1774-\u177F\u17D4-\u17D6\u17D8-\u17DB\u17DE\u17DF\u17EA-\u180A\u180E\u180F\u181A-\u181F\u1879-\u187F\u18AB-\u18AF\u18F6-\u18FF\u191F\u192C-\u192F\u193C-\u1945\u196E\u196F\u1975-\u197F\u19AC-\u19AF\u19CA-\u19CF\u19DA-\u19FF\u1A1C-\u1A1F\u1A5F\u1A7D\u1A7E\u1A8A-\u1A8F\u1A9A-\u1AA6\u1AA8-\u1AAF\u1AC1-\u1AFF\u1B4C-\u1B4F\u1B5A-\u1B6A\u1B74-\u1B7F\u1BF4-\u1BFF\u1C38-\u1C3F\u1C4A-\u1C4C\u1C7E\u1C7F\u1C89-\u1C8F\u1CBB\u1CBC\u1CC0-\u1CCF\u1CD3\u1CFB-\u1CFF\u1DFA\u1F16\u1F17\u1F1E\u1F1F\u1F46\u1F47\u1F4E\u1F4F\u1F58\u1F5A\u1F5C\u1F5E\u1F7E\u1F7F\u1FB5\u1FBD\u1FBF-\u1FC1\u1FC5\u1FCD-\u1FCF\u1FD4\u1FD5\u1FDC-\u1FDF\u1FED-\u1FF1\u1FF5\u1FFD-\u203E\u2041-\u2053\u2055-\u2070\u2072-\u207E\u2080-\u208F\u209D-\u20CF\u20F1-\u2101\u2103-\u2106\u2108\u2109\u2114\u2116-\u2118\u211E-\u2123\u2125\u2127\u2129\u212E\u213A\u213B\u2140-\u2144\u214A-\u214D\u214F-\u215F\u2189-\u24B5\u24EA-\u2BFF\u2C2F\u2C5F\u2CE5-\u2CEA\u2CF4-\u2CFF\u2D26\u2D28-\u2D2C\u2D2E\u2D2F\u2D68-\u2D6E\u2D70-\u2D7E\u2D97-\u2D9F\u2DA7\u2DAF\u2DB7\u2DBF\u2DC7\u2DCF\u2DD7\u2DDF\u2E00-\u2E2E\u2E30-\u3004\u3008-\u3020\u3030\u3036\u3037\u303D-\u3040\u3097\u3098\u309B\u309C\u30A0\u30FB\u3100-\u3104\u3130\u318F-\u319F\u31C0-\u31EF\u3200-\u33FF\u4DC0-\u4DFF\u9FFD-\u9FFF\uA48D-\uA4CF\uA4FE\uA4FF\uA60D-\uA60F\uA62C-\uA63F\uA673\uA67E\uA6F2-\uA716\uA720\uA721\uA789\uA78A\uA7C0\uA7C1\uA7CB-\uA7F4\uA828-\uA82B\uA82D-\uA83F\uA874-\uA87F\uA8C6-\uA8CF\uA8DA-\uA8DF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA954-\uA95F\uA97D-\uA97F\uA9C1-\uA9CE\uA9DA-\uA9DF\uA9FF\uAA37-\uAA3F\uAA4E\uAA4F\uAA5A-\uAA5F\uAA77-\uAA79\uAAC3-\uAADA\uAADE\uAADF\uAAF0\uAAF1\uAAF7-\uAB00\uAB07\uAB08\uAB0F\uAB10\uAB17-\uAB1F\uAB27\uAB2F\uAB5B\uAB6A-\uAB6F\uABEB\uABEE\uABEF\uABFA-\uABFF\uD7A4-\uD7AF\uD7C7-\uD7CA\uD7FC-\uD7FF\uE000-\uF8FF\uFA6E\uFA6F\uFADA-\uFAFF\uFB07-\uFB12\uFB18-\uFB1C\uFB29\uFB37\uFB3D\uFB3F\uFB42\uFB45\uFBB2-\uFBD2\uFD3E-\uFD4F\uFD90\uFD91\uFDC8-\uFDEF\uFDFC-\uFDFF\uFE10-\uFE1F\uFE30-\uFE32\uFE35-\uFE4C\uFE50-\uFE6F\uFE75\uFEFD-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF3E\uFF40\uFF5B-\uFF65\uFFBF-\uFFC1\uFFC8\uFFC9\uFFD0\uFFD1\uFFD8\uFFD9\uFFDD-\uFFFF]|\uD800[\uDC0C\uDC27\uDC3B\uDC3E\uDC4E\uDC4F\uDC5E-\uDC7F\uDCFB-\uDD3F\uDD75-\uDDFC\uDDFE-\uDE7F\uDE9D-\uDE9F\uDED1-\uDEDF\uDEE1-\uDEFF\uDF20-\uDF2C\uDF4B-\uDF4F\uDF7B-\uDF7F\uDF9E\uDF9F\uDFC4-\uDFC7\uDFD0\uDFD6-\uDFFF]|\uD801[\uDC9E\uDC9F\uDCAA-\uDCAF\uDCD4-\uDCD7\uDCFC-\uDCFF\uDD28-\uDD2F\uDD64-\uDDFF\uDF37-\uDF3F\uDF56-\uDF5F\uDF68-\uDFFF]|\uD802[\uDC06\uDC07\uDC09\uDC36\uDC39-\uDC3B\uDC3D\uDC3E\uDC56-\uDC5F\uDC77-\uDC7F\uDC9F-\uDCDF\uDCF3\uDCF6-\uDCFF\uDD16-\uDD1F\uDD3A-\uDD7F\uDDB8-\uDDBD\uDDC0-\uDDFF\uDE04\uDE07-\uDE0B\uDE14\uDE18\uDE36\uDE37\uDE3B-\uDE3E\uDE40-\uDE5F\uDE7D-\uDE7F\uDE9D-\uDEBF\uDEC8\uDEE7-\uDEFF\uDF36-\uDF3F\uDF56-\uDF5F\uDF73-\uDF7F\uDF92-\uDFFF]|\uD803[\uDC49-\uDC7F\uDCB3-\uDCBF\uDCF3-\uDCFF\uDD28-\uDD2F\uDD3A-\uDE7F\uDEAA\uDEAD-\uDEAF\uDEB2-\uDEFF\uDF1D-\uDF26\uDF28-\uDF2F\uDF51-\uDFAF\uDFC5-\uDFDF\uDFF7-\uDFFF]|\uD804[\uDC47-\uDC65\uDC70-\uDC7E\uDCBB-\uDCCF\uDCE9-\uDCEF\uDCFA-\uDCFF\uDD35\uDD40-\uDD43\uDD48-\uDD4F\uDD74\uDD75\uDD77-\uDD7F\uDDC5-\uDDC8\uDDCD\uDDDB\uDDDD-\uDDFF\uDE12\uDE38-\uDE3D\uDE3F-\uDE7F\uDE87\uDE89\uDE8E\uDE9E\uDEA9-\uDEAF\uDEEB-\uDEEF\uDEFA-\uDEFF\uDF04\uDF0D\uDF0E\uDF11\uDF12\uDF29\uDF31\uDF34\uDF3A\uDF45\uDF46\uDF49\uDF4A\uDF4E\uDF4F\uDF51-\uDF56\uDF58-\uDF5C\uDF64\uDF65\uDF6D-\uDF6F\uDF75-\uDFFF]|\uD805[\uDC4B-\uDC4F\uDC5A-\uDC5D\uDC62-\uDC7F\uDCC6\uDCC8-\uDCCF\uDCDA-\uDD7F\uDDB6\uDDB7\uDDC1-\uDDD7\uDDDE-\uDDFF\uDE41-\uDE43\uDE45-\uDE4F\uDE5A-\uDE7F\uDEB9-\uDEBF\uDECA-\uDEFF\uDF1B\uDF1C\uDF2C-\uDF2F\uDF3A-\uDFFF]|\uD806[\uDC3B-\uDC9F\uDCEA-\uDCFE\uDD07\uDD08\uDD0A\uDD0B\uDD14\uDD17\uDD36\uDD39\uDD3A\uDD44-\uDD4F\uDD5A-\uDD9F\uDDA8\uDDA9\uDDD8\uDDD9\uDDE2\uDDE5-\uDDFF\uDE3F-\uDE46\uDE48-\uDE4F\uDE9A-\uDE9C\uDE9E-\uDEBF\uDEF9-\uDFFF]|\uD807[\uDC09\uDC37\uDC41-\uDC4F\uDC5A-\uDC71\uDC90\uDC91\uDCA8\uDCB7-\uDCFF\uDD07\uDD0A\uDD37-\uDD39\uDD3B\uDD3E\uDD48-\uDD4F\uDD5A-\uDD5F\uDD66\uDD69\uDD8F\uDD92\uDD99-\uDD9F\uDDAA-\uDEDF\uDEF7-\uDFAF\uDFB1-\uDFFF]|\uD808[\uDF9A-\uDFFF]|\uD809[\uDC6F-\uDC7F\uDD44-\uDFFF]|[\uD80A\uD80B\uD80E-\uD810\uD812-\uD819\uD824-\uD82B\uD82D\uD82E\uD830-\uD833\uD837\uD839\uD83D\uD83F\uD87B-\uD87D\uD87F\uD885-\uDB3F\uDB41-\uDBFF][\uDC00-\uDFFF]|\uD80D[\uDC2F-\uDFFF]|\uD811[\uDE47-\uDFFF]|\uD81A[\uDE39-\uDE3F\uDE5F\uDE6A-\uDECF\uDEEE\uDEEF\uDEF5-\uDEFF\uDF37-\uDF3F\uDF44-\uDF4F\uDF5A-\uDF62\uDF78-\uDF7C\uDF90-\uDFFF]|\uD81B[\uDC00-\uDE3F\uDE80-\uDEFF\uDF4B-\uDF4E\uDF88-\uDF8E\uDFA0-\uDFDF\uDFE2\uDFE5-\uDFEF\uDFF2-\uDFFF]|\uD821[\uDFF8-\uDFFF]|\uD823[\uDCD6-\uDCFF\uDD09-\uDFFF]|\uD82C[\uDD1F-\uDD4F\uDD53-\uDD63\uDD68-\uDD6F\uDEFC-\uDFFF]|\uD82F[\uDC6B-\uDC6F\uDC7D-\uDC7F\uDC89-\uDC8F\uDC9A-\uDC9C\uDC9F-\uDFFF]|\uD834[\uDC00-\uDD64\uDD6A-\uDD6C\uDD73-\uDD7A\uDD83\uDD84\uDD8C-\uDDA9\uDDAE-\uDE41\uDE45-\uDFFF]|\uD835[\uDC55\uDC9D\uDCA0\uDCA1\uDCA3\uDCA4\uDCA7\uDCA8\uDCAD\uDCBA\uDCBC\uDCC4\uDD06\uDD0B\uDD0C\uDD15\uDD1D\uDD3A\uDD3F\uDD45\uDD47-\uDD49\uDD51\uDEA6\uDEA7\uDEC1\uDEDB\uDEFB\uDF15\uDF35\uDF4F\uDF6F\uDF89\uDFA9\uDFC3\uDFCC\uDFCD]|\uD836[\uDC00-\uDDFF\uDE37-\uDE3A\uDE6D-\uDE74\uDE76-\uDE83\uDE85-\uDE9A\uDEA0\uDEB0-\uDFFF]|\uD838[\uDC07\uDC19\uDC1A\uDC22\uDC25\uDC2B-\uDCFF\uDD2D-\uDD2F\uDD3E\uDD3F\uDD4A-\uDD4D\uDD4F-\uDEBF\uDEFA-\uDFFF]|\uD83A[\uDCC5-\uDCCF\uDCD7-\uDCFF\uDD4C-\uDD4F\uDD5A-\uDFFF]|\uD83B[\uDC00-\uDDFF\uDE04\uDE20\uDE23\uDE25\uDE26\uDE28\uDE33\uDE38\uDE3A\uDE3C-\uDE41\uDE43-\uDE46\uDE48\uDE4A\uDE4C\uDE50\uDE53\uDE55\uDE56\uDE58\uDE5A\uDE5C\uDE5E\uDE60\uDE63\uDE65\uDE66\uDE6B\uDE73\uDE78\uDE7D\uDE7F\uDE8A\uDE9C-\uDEA0\uDEA4\uDEAA\uDEBC-\uDFFF]|\uD83C[\uDC00-\uDD2F\uDD4A-\uDD4F\uDD6A-\uDD6F\uDD8A-\uDFFF]|\uD83E[\uDC00-\uDFEF\uDFFA-\uDFFF]|\uD869[\uDEDE-\uDEFF]|\uD86D[\uDF35-\uDF3F]|\uD86E[\uDC1E\uDC1F]|\uD873[\uDEA2-\uDEAF]|\uD87A[\uDFE1-\uDFFF]|\uD87E[\uDE1E-\uDFFF]|\uD884[\uDF4B-\uDFFF]|\uDB40[\uDC00-\uDCFF\uDDF0-\uDFFF]'
        #s = unicodedata.normalize('NFKC', s)
        #s = s.lower() if lower else s
        #s = re.sub(regex_bad_chars, '', s)
        ##s = re.sub(r'[^-_\w]', space, s)
        #s = re.sub(r'\s', space, s)
        return s 
    
    def _relative_url_(self, url):
        # https://jekyllrb.com/docs/liquid/filters/#relative-url
        url = str(url) if url else ''
        base_url = self.ctx.get('site', {}).get('baseurl', '')
        if base_url:
            return os.path.join('/' + base_url.lstrip('/'), url.lstrip('/'))
        return ('.' + url) if url.startswith('/') else url

    def _absolute_url_(self, url):
        # https://jekyllrb.com/docs/liquid/filters/#absolute-url
        url = str(url) if url else ''
        site_url = self.ctx.get('site', {}).get('url', '')
        base_url = self.ctx.get('site', {}).get('baseurl', '')
        if site_url:
            return os.path.join(site_url, base_url.lstrip('/'), url.lstrip('/'))
        if base_url:
            return os.path.join('/' + base_url.lstrip('/'), url.lstrip('/'))
        return ('.' + url) if url.startswith('/') else url
    
    @staticmethod
    def _where_exp_(xs, key, value):
        # https://jekyllrb.com/docs/liquid/filters/#where-expression
        expr = eval(f'lambda {key}: {value}', dict(nil = None, false = False, true = True))
        return [x for x in xs if expr(NanoJekyllContext(x))] if xs else []

    @staticmethod
    def _find_(xs, key, value):
        # https://jekyllrb.com/docs/liquid/filters/#find
        res = NanoJekyllContext._where_(xs, key, value)
        return (res + [None])[0]

    @staticmethod
    def _find_exp_(xs, key, value):
        # https://jekyllrb.com/docs/liquid/filters/#find-expression
        res = NanoJekyllContext._where_exp_(xs, key, value)
        return (res + [None])[0]

    @staticmethod
    def _group_by_(xs, key):
        # https://jekyllrb.com/docs/liquid/filters/#group-by
        expr = lambda item: getattr(NanoJekyllContext(item), key, None)
        return [dict(name = k, items = list(g)) for k, g in itertools.groupby(sorted(xs, key = expr), key = expr)]

    @staticmethod
    def _group_by_exp_(xs, key, value):
        # https://jekyllrb.com/docs/liquid/filters/#group-by-expression
        expr_ = eval(f'lambda {key}: {value}', dict(nil = None, false = False, true = True))
        expr = lambda item: expr_(NanoJekyllContext(item))
        return [dict(name = k, items = list(g)) for k, g in itertools.groupby(sorted(xs, key = expr), key = expr)]
    
    @staticmethod
    def _cgi_escape_(x):
        # https://jekyllrb.com/docs/liquid/filters/#cgi-escape
        return urllib.parse.quote_plus(str(x)) if x else ''

    @staticmethod
    def _uri_escape_(x):
        # https://jekyllrb.com/docs/liquid/filters/#uri-escape
        return urllib.parse.quote(str(x)) if x else ''
    
    @staticmethod
    def _markdownify_(x, extensions = ['meta', 'tables', 'toc']):
        # https://jekyllrb.com/docs/liquid/filters/#markdownify
        try:
            # pip install markdown
            import markdown
        except:
            return x
        return markdown.markdown(x, extensions = extensions)
    
    @staticmethod
    def _sassify_(x):
        # https://jekyllrb.com/docs/liquid/filters/#converting-sass-scss
        try:
            # pip install libsass
            # unfortunately libsass is deprecated and not updated: https://github.com/sass/libsass/issues/3187#issuecomment-1913740874
            import sass
        except:
            return x
        return sass.compile(string = x)

    @staticmethod
    def _scssify_(x):
        # https://jekyllrb.com/docs/liquid/filters/#converting-sass-scss
        return NanoJekyllContext._sassify_(x)
    
    @staticmethod
    def _normalize_whitespace_(x):
        # https://jekyllrb.com/docs/liquid/filters/#normalize-whitespace
        return ' '.join(str(x).split()) if x else ''
    
    @staticmethod
    def _xml_escape_(s):
        # https://jekyllrb.com/docs/liquid/filters/#xml-escape
        # https://github.com/jekyll/jekyll/blob/96a4198c27482f061e145953066af501d5e085e2/lib/jekyll/filters.rb#L77
        return html.escape(str(s)) if s else ''
    
    @staticmethod
    def _to_integer_(x):
        # https://jekyllrb.com/docs/liquid/filters/#to-integer
        return int(x)

    @staticmethod
    def _number_of_words_(x, mode = ''):
        # https://jekyllrb.com/docs/liquid/filters/#number-of-words
        if not x:
            return 0
        if mode in ['cjk', 'auto']:
            return len(re.findall(r'[\u4e00-\u9FFF]|[\u3040-\u30ff]|[\uac00-\ud7a3]', str(x)))
        return len(str(x).split())

    @staticmethod
    def _array_to_sentence_(xs, y = 'and'):
        # https://jekyllrb.com/docs/liquid/filters/#array-to-sentence
        return ((', '.join(str(x) for x in xs[:-1]) + f', {y} ' + xs[-1]) if len(xs) > 2 else f' {y} '.join(str(x) for x in xs) if len(xs) == 2 else str(xs[0])) if xs else ''

    @staticmethod
    def _jsonify_(x):
        # https://jekyllrb.com/docs/liquid/filters/#data-to-json
        return json.dumps(x, ensure_ascii = False) if x else '{}'
    
    @staticmethod
    def _inspect_(x):
        # https://jekyllrb.com/docs/liquid/filters/#inspect
        return repr(x)
    
    @staticmethod
    def _smartify_(x):
        # https://jekyllrb.com/docs/liquid/filters/#smartify
        return str(x) if x else ''

    @staticmethod
    def _unshift_(xs, elem):
        # https://jekyllrb.com/docs/liquid/filters/#array-filters
        return [elem] + (xs or [])
    
    @staticmethod
    def _push_(xs, elem):
        # https://jekyllrb.com/docs/liquid/filters/#array-filters
        return (xs or []) + [elem]
    
    @staticmethod
    def _pop_(xs):
        # https://jekyllrb.com/docs/liquid/filters/#array-filters
        return xs[:-1] if xs else []
    
    @staticmethod
    def _shift_(xs):
        # https://jekyllrb.com/docs/liquid/filters/#array-filters
        return xs[1:] if xs else []



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

class NanoJekyllPluginFeedMeta(NanoJekyllTemplate):
    template_code = '''
<link type="application/atom+xml" rel="alternate" href='{{ site.feed.path | default: "feed.xml" }}' title="{{ site.title }}" />
'''
    #def __str__(self): return ' ' * 4 * self.indent_level + 'def render_{template_name}(self):\n'.format(template_name = self.template_name) + self.template_code.replace('{{ site.feed.path | default: "feed.xml" }}', self._default_(str(self.site.feed.path), "feed.xml")).replace('{{ site.title }}', str(self.page.title))'''


class NanoJekyllPluginFeedMetaXml(NanoJekyllTemplate):
    # https://github.com/jekyll/jekyll-feed/blob/master/lib/jekyll-feed/feed.xml
    template_code = '''
<?xml version="1.0" encoding="utf-8"?>
{% if page.xsl %}
  <?xml-stylesheet type="text/xml" href="{{ '/feed.xslt.xml' | absolute_url }}"?>
{% endif %}
<feed xmlns="http://www.w3.org/2005/Atom" {% if site.lang %}xml:lang="{{ site.lang }}"{% endif %}>
  <generator uri="https://jekyllrb.com/" version="{{ jekyll.version }}">Jekyll</generator>
  <link href="{{ page.url | absolute_url }}" rel="self" type="application/atom+xml" />
  <link href="{{ '/' | absolute_url }}" rel="alternate" type="text/html" {% if site.lang %}hreflang="{{ site.lang }}" {% endif %}/>
  <updated>{{ site.time | date_to_xmlschema }}</updated>
  <id>{{ page.url | absolute_url | xml_escape }}</id>

  {% assign title = site.title | default: site.name %}
  {% if page.collection != "posts" %}
    {% assign collection = page.collection | capitalize %}
    {% assign title = title | append: " | " | append: collection %}
  {% endif %}
  {% if page.category %}
    {% assign category = page.category | capitalize %}
    {% assign title = title | append: " | " | append: category %}
  {% endif %}

  {% if title %}
    <title type="html">{{ title | smartify | xml_escape }}</title>
  {% endif %}

  {% if site.description %}
    <subtitle>{{ site.description | xml_escape }}</subtitle>
  {% endif %}

  {% if site.author %}
    <author>
        <name>{{ site.author.name | default: site.author | xml_escape }}</name>
      {% if site.author.email %}
        <email>{{ site.author.email | xml_escape }}</email>
      {% endif %}
      {% if site.author.uri %}
        <uri>{{ site.author.uri | xml_escape }}</uri>
      {% endif %}
    </author>
  {% endif %}

  {% if page.tags %}
    {% assign posts = site.tags[page.tags] %}
  {% else %}
    {% assign posts = site[page.collection] %}
  {% endif %}
  {% if page.category %}
    {% assign posts = posts | where: "categories", page.category %}
  {% endif %}
  {% unless site.show_drafts %}
    {% assign posts = posts | where_exp: "post", "post.draft != true" %}
  {% endunless %}
  {% assign posts = posts | sort: "date" | reverse %}
  {% assign posts_limit = site.feed.posts_limit | default: 10 %}
  {% for post in posts limit: posts_limit %}
    <entry{% if post.lang %}{{" "}}xml:lang="{{ post.lang }}"{% endif %}>
      {% assign post_title = post.title | smartify | strip_html | normalize_whitespace | xml_escape %}

      <title type="html">{{ post_title }}</title>
      <link href="{{ post.url | absolute_url }}" rel="alternate" type="text/html" title="{{ post_title }}" />
      <published>{{ post.date | date_to_xmlschema }}</published>
      <updated>{{ post.last_modified_at | default: post.date | date_to_xmlschema }}</updated>
      <id>{{ post.id | absolute_url | xml_escape }}</id>
      {% assign excerpt_only = post.feed.excerpt_only | default: site.feed.excerpt_only %}
      {% unless excerpt_only %}
        <content type="html" xml:base="{{ post.url | absolute_url | xml_escape }}"><![CDATA[{{ post.content | strip }}]]></content>
      {% endunless %}

      {% assign post_author = post.author | default: post.authors[0] | default: site.author %}
      {% assign post_author = site.data.authors[post_author] | default: post_author %}
      {% assign post_author_email = post_author.email | default: nil %}
      {% assign post_author_uri = post_author.uri | default: nil %}
      {% assign post_author_name = post_author.name | default: post_author %}

      <author>
          <name>{{ post_author_name | default: "" | xml_escape }}</name>
        {% if post_author_email %}
          <email>{{ post_author_email | xml_escape }}</email>
        {% endif %}
        {% if post_author_uri %}
          <uri>{{ post_author_uri | xml_escape }}</uri>
        {% endif %}
      </author>

      {% if post.category %}
        <category term="{{ post.category | xml_escape }}" />
      {% elsif post.categories %}
        {% for category in post.categories %}
          <category term="{{ category | xml_escape }}" />
        {% endfor %}
      {% endif %}

      {% for tag in post.tags %}
        <category term="{{ tag | xml_escape }}" />
      {% endfor %}

      {% assign post_summary = post.description | default: post.excerpt %}
      {% if post_summary and post_summary != empty %}
        <summary type="html"><![CDATA[{{ post_summary | strip_html | normalize_whitespace }}]]></summary>
      {% endif %}

      {% assign post_image = post.image.path | default: post.image %}
      {% if post_image %}
        {% unless post_image contains "://" %}
          {% assign post_image = post_image | absolute_url %}
        {% endunless %}
        <media:thumbnail xmlns:media="http://search.yahoo.com/mrss/" url="{{ post_image | xml_escape }}" />
        <media:content medium="image" url="{{ post_image | xml_escape }}" xmlns:media="http://search.yahoo.com/mrss/" />
      {% endif %}
    </entry>
  {% endfor %}
</feed>
'''
