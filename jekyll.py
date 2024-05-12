# https://github.com/aosabook/500lines/tree/master/template-engine as a starting point

import os, sys, re, html, datetime
import inspect

class NanoJekyll:
    def __init__(self, base_dir = '.', includes_dirname = '_includes', layouts_dirname = '_layouts', global_variables = ['site', 'page', 'layout', 'theme', 'content', 'paginator']):
        # https://jekyllrb.com/docs/variables/
        self.global_variables = global_variables
        self.layouts = {basename : self.read_template(os.path.join(base_dir, layouts_dirname, basename)) for basename in os.listdir(os.path.join(base_dir, layouts_dirname)) if os.path.isfile(os.path.join(base_dir, layouts_dirname, basename))}
        self.includes = {basename : self.read_template(os.path.join(base_dir, includes_dirname, basename)) for basename in os.listdir(os.path.join(base_dir, includes_dirname)) if os.path.isfile(os.path.join(base_dir, includes_dirname, basename))}

    @staticmethod
    def read_template(path, front_matter_sep = '---\n'):
        front_matter = ''
        template = ''
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
    def extract_layout_from_frontmatter(frontmatter):
        return ([line.split(':')[1].strip() for line in frontmatter.splitlines() if line.strip().replace(' ', '').startswith('layout:')] or [None])[0]

    def render(self, ctx = {}, layout = ''):
        # https://jekyllrb.com/docs/rendering-process/
        content = ''
        while layout:
            frontmatter, template = [l for k, l in self.layouts.items() if k == layout or os.path.splitext(k)[0] == layout][0] 
            content = NanoJekyllTemplate(template, includes = self.includes, global_variables = self.global_variables).render(ctx = ctx | dict(content = content))
            layout = self.extract_layout_from_frontmatter(frontmatter)
        return content

class NanoJekyllTemplate:
    INDENT_STEP = 4

    def render(self, ctx = {}):
        return self.render_cls(ctx).render()
    
    def add_line(self, line = ''):
        self.code.extend([' ' * self.indent_level, line, "\n"])
    
    def indent(self):
        self.indent_level += self.INDENT_STEP
    
    def dedent(self):
        self.indent_level -= self.INDENT_STEP
    
    def __str__(self):
        return ''.join(str(c) for c in self.code)
    
    def get_globals(self):
        # A check that the caller really finished all the blocks they started.
        assert self.indent_level == 0
        python_source = str(self)
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace
    
    def __init__(self, template_code, includes = {}, global_variables = []):
        self.includes = includes
        self.global_variables = global_variables

        self.code = []
        self.indent_level = 0
    
        split_tokens = lambda s: re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", s)


        self.add_line('import os, sys, re, html, datetime')
        self.add_line()
        self.add_line(inspect.getsource(NanoJekyllValue))
        self.indent()
        self.indent()
        self.add_line()

        if self.global_variables:
            self.add_line(', '.join(self.global_variables) + ' = ' +  ', '.join(f'NanoJekyllValue(self.ctx.get("{k}"))' for k in self.global_variables))

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
                self.add_line("result.append(TrimLeft())")

            if token.startswith('{{'):
                expr = self._expr_code(token_inner)
                self.add_line(f"result.append(str({expr}))")

            elif token.startswith('{%'):
                # Action tag: split into words and parse further.
                #flush_output()
                #token_inner = token[b:e].strip()
                #words = token_inner.split()
                if words[0] == '-':
                    del words[0]
                if words[-1] == '-':
                    del words[-1]

                if words[0] == 'comment':
                    tokens_i_end = tokens[i].replace(' ', '').replace('comment', 'endcomment')
                    while tokens[i].replace(' ', '') != tokens_i_end:
                        i += 1

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
                    #self.add_line('#include ' + words[-1])
                    template_name = words[1]
                    if len(words) > 2:
                        self.add_line('include = NanoJekyllValue(dict(' + ', '.join(words[k] + words[k + 1] + words[k + 2]  for k in range(2, len(words), 3)) + '))')
                        
                    frontmatter_include, template_include = self.includes[template_name]
                    tokens = tokens[:i + 1] + split_tokens(template_include) + tokens[i + 1:]
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    self.add_line('{} = {}'.format(var_name, expr))

                elif words[0] == 'seo':
                    self.add_line('#seo#')
        
                else:
                    assert False, ("Don't understand tag: " + words[0])

            else:
                if token:
                    self.add_line("result.append({})".format(repr(token)))
            
            if e == -3:
                self.add_line("result.append(TrimRight())")
            i += 1

        assert not ops_stack, ("Unmatched action tag: " + ops_stack[-1])

        self.add_line('return finalize_result(result)')
        self.dedent()
        self.dedent()
        assert self.indent_level == 0
        
        #print(str(code), file = sys.stderr)
        print(str(self), file = open('render.py', 'w'))

        self.render_cls = self.get_globals()['NanoJekyllValue']
    
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
                    code = f'{code} | {func_name}()'
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    code = f'{code} | {func_name}({func_args})'
                    
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
        yield from (self.ctx if self.ctx else [])

    @staticmethod
    def pipify(f):
        return (lambda *args: (f, *args))
    
    # https://shopify.github.io/liquid/basics/operators/
    # https://jekyllrb.com/docs/liquid/filters/

    @staticmethod
    def relative_url(url):
        # https://jekyllrb.com/docs/liquid/filters/
        return url

    @staticmethod
    def absolute_url(url):
        # https://jekyllrb.com/docs/liquid/filters/
        return url
    
    @staticmethod
    def date_to_xmlschema(dt):
        pass
    
    @staticmethod
    def date(dt, date_format):
        # https://shopify.github.io/liquid/filters/date/
        return dt.strftime(date_format)

    @staticmethod
    def escape(s):
        # https://shopify.github.io/liquid/filters/escape/
        return html.escape(str(s)) if s else ''
    
    @staticmethod
    def default(s, t):
        # https://shopify.github.io/liquid/filters/default/
        return s or t

    @staticmethod
    def where(xs, key, value):
        # https://shopify.github.io/liquid/filters/where/
        return [x for x in xs if x[key] == value]

    @staticmethod
    def map(xs, key):
        # https://shopify.github.io/liquid/filters/map/
        return [x[key] for x in xs] if xs else []
    
    @staticmethod
    def append(xs, item):
        # https://shopify.github.io/liquid/filters/append/
        return str(xs or '') + str(item or '')

    @staticmethod
    def first(xs):
        # https://shopify.github.io/liquid/filters/first/
        return xs[0] if xs else None

    @staticmethod
    def size(xs):
        # https://shopify.github.io/liquid/filters/size/
        return len(xs)

    @staticmethod
    def join(xs, sep):
        # https://shopify.github.io/liquid/filters/join/
        return sep.join(str(x) for x in xs)

    @staticmethod
    def remove(x, y):
        return x.replace(y, '')

    @staticmethod
    def jsonify(x):
        return json.dumps(x, ensure_ascii = False)

    @staticmethod
    def xml_escape(x):
        return x

    @staticmethod
    def capitalize(x):
        return x

    @staticmethod
    def smartify(x):
        return x

    @staticmethod
    def where_exp(x, y):
        return x

    @staticmethod
    def sort(x):
        return sorted(x)
    
    @staticmethod
    def reverse(x):
        return list(reversed(x))

    @staticmethod
    def strip(x):
        return x

    @staticmethod
    def strip_html(x):
        return x

    @staticmethod
    def normalize_whitespace(x):
        return x

    def render(self):
        # https://shopify.github.io/liquid/tags/iteration/#forloop-object
        nil, false, true = None, False, True
        class TrimLeft(str): pass
        class TrimRight(str): pass
        class forloop: index = 1; last = False; first = False; index0 = 0; length = None; rindex = -1;
        def finalize_result(result): return "".join(result)
        result = []
        globals().update({k: self.pipify(getattr(self, k)) for k in dir(self) if k != "ctx" and not k.startswith("__")})
        globals().update({k : NanoJekyllValue(v) for k, v in self.ctx.items()})
        
