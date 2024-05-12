# https://github.com/aosabook/500lines/tree/master/template-engine as a starting point

import os, sys, re, html, datetime
import inspect

class NanoJekyll:
    def __init__(self, base_dir = '.', includes_dirname = '_includes', layouts_dirname = '_layouts'):
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
            content = NanoJekyllTemplate(template, ctx = dict(includes = self.includes)).render(ctx = ctx | dict(content = content))
            layout = self.extract_layout_from_frontmatter(frontmatter)
        return content

class NanoJekyllCodeBuilder:
    INDENT_STEP = 4
    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent
    def __str__(self):
        return ''.join(str(c) for c in self.code)
    def add_line(self, line = ''):
        self.code.extend([' ' * self.indent_level, line, "\n"])
    def indent(self):
        self.indent_level += self.INDENT_STEP
    def dedent(self):
        self.indent_level -= self.INDENT_STEP
    def get_globals(self):
        # A check that the caller really finished all the blocks they started.
        assert self.indent_level == 0
        python_source = str(self)
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace

class NanoJekyllTemplate:
    def render(self, ctx = {}):
        obj = self.render_cls(self.ctx | (ctx or {}))
        return obj.render()
    
    def __init__(self, template_code, ctx = {}):
        self.ctx = ctx
    
        split_tokens = lambda s: re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", s)


        code = NanoJekyllCodeBuilder()
        code.add_line('import os, sys, re, html, datetime')
        code.add_line()
        code.add_line(inspect.getsource(NanoJekyllValue))
        code.indent()
        code.indent()
        code.add_line()


        tokens = split_tokens(template_code)
        
        ops_stack = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            b = 3 if token.startswith('{%-') or token.startswith('{{-') else 2
            e = -3 if token.endswith('-%}') or token.endswith('-}}') else -2
            
            if b == 3:
                code.add_line("result.append(TrimLeft())")

            if token.startswith('{#'):
                i += 1
                continue

            elif token.startswith('{{'):
                token_inner = token[b:e].strip()
                expr = self._expr_code(token_inner)
                code.add_line(f"result.append(str({expr}))")

            elif token.startswith('{%'):
                # Action tag: split into words and parse further.
                #flush_output()
                token_inner = token[b:e].strip()
                words = token_inner.split()
                if words[0] == '-':
                    del words[0]
                if words[-1] == '-':
                    del words[-1]

                if words[0] == 'if':
                    ops_stack.append('if')
                    code.add_line("if {}:".format(' '.join(words[1:])))
                    code.indent()
                
                elif words[0] == 'else':
                    #ops_stack.append('else')
                    code.dedent()
                    code.add_line("else:".format(' '.join(words[1:])))
                    code.indent()
                
                elif words[0] == 'unless':
                    ops_stack.append('unless')
                    code.add_line("if not( {} ):".format(' '.join(words[1:])))
                    code.indent()
                
                elif words[0] == 'for':
                    # A loop: iterate over expression result.
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    code.add_line("for {} in {}:".format(words[1], self._expr_code(words[3]) ) )
                    code.indent()
                
                elif words[0].startswith('end'):
                    # Endsomething.  Pop the ops stack.
                    if len(words) != 1:
                        self._syntax_error("Don't understand end", token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error("Too many ends", token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        print('start:', start_what, 'end:', end_what)
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()

                elif words[0] == 'include':
                    #code.add_line('#include ' + words[-1])
                    template_name = words[1]
                    if len(words) > 2:
                        code.add_line('include = NanoJekyllValue(dict(' + ', '.join(words[k] + words[k + 1] + words[k + 2]  for k in range(2, len(words), 3)) + '))')
                        
                    frontmatter_include, template_include = self.ctx.get('includes', {})[template_name]
                    tokens = tokens[:i + 1] + split_tokens(template_include) + tokens[i + 1:]
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    code.add_line('{} = {}'.format(var_name, expr))

                elif words[0] == 'seo':
                    code.add_line('#seo#')
        
                else:
                    self._syntax_error("Don't understand tag", words[0])

            else:
                if token:
                    code.add_line("result.append({})".format(repr(token)))
            
            if e == -3:
                code.add_line("result.append(TrimRight())")
            i += 1

        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        code.add_line('return finalize_result(result)')
        code.dedent()
        code.dedent()
        assert code.indent_level == 0
        
        #print(str(code), file = sys.stderr)
        print(str(code), file = open('render.py', 'w'))

        self.render_cls = code.get_globals()['NanoJekyllValue']
    
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
                #self._variable(func_name, self.all_vars)
                if not func_args:
                    #code = f"{func_name}({code})"
                    code = f'{code} | {func_name}()'
                    #code = f"context['{func_name}']({code})"
                    #code = "c_%s(%s)" % (func_name, code)
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    #code = f"{func_name}({code}, {func_args})"
                    code = f'{code} | {func_name}({func_args})'
                    #code = "c_%s(%s, %s)" % (func_name, code, self._expr_code(func_args[0]))
                    
        elif "." in expr:
            #self._variable(expr.split(".")[0], self.all_vars)
            code = expr
            #args = ", ".join(repr(d) for d in dots[1:])
            #code = "do_dots(%s, %s)" % (code, args)
        else:
            #self._variable(expr, self.all_vars)
            code = "%s" % expr
        return code

    def _syntax_error(self, msg, thing):
        raise ValueError(f"{msg}: {thing=}")

    def _variable(self, name, vars_set):
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)

class NanoJekyllValue:
    # https://shopify.github.io/liquid/basics/operators/
    def __init__(self, val = None):
        self.val = val.val if isinstance(val, NanoJekyllValue) else val
    
    def __or__(self, other):
        return NanoJekyllValue(other[0](self.val, *other[1:]))

    def __str__(self):
        return str(self.val) if self.val else ''

    def __bool__(self):
        return bool(self.val)

    def __gt__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return self.val > other

    def __ge__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return self.val >= other

    def __lt__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return self.val < other

    def __le__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return sefl.val <= other

    def __eq__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return self.val == other

    def __ne__(self, other):
        other = other.val if isinstance(other, NanoJekyllValue) else other
        return self.val != other
        
    def __getattr__(self, key):
        if isinstance(self.val, dict):
            if key in self.val:
                return NanoJekyllValue(self.val[key])
        return NanoJekyllValue(getattr(self.val, key, None))
    
    def __getitem__(self, index):
        if isinstance(self.val, (list, str)):
            return NanoJekyllValue(self.val[index])
        if isinstance(self.val, dict):
            return NanoJekyllValue(self.val.get(index))
        return NanoJekyllValue(None)

    def __len__(self):
        return len(self.val) if isinstance(self.val, (list, dict, str)) else None

    def __iter__(self):
        yield from (self.val if self.val else [])

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
        globals().update({k: self.pipify(getattr(self, k)) for k in dir(self) if k != "val" and not k.startswith("__")})
        globals().update({k : NanoJekyllValue(v) for k, v in self.val.items()})
        
