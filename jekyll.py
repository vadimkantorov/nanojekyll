# https://github.com/aosabook/500lines/tree/master/template-engine as a starting point

import os
import re
import sys
import datetime
import html

class CodeBuilder:
    INDENT_STEP = 4
    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent
    def __str__(self):
        return "".join(str(c) for c in self.code)
    def add_line(self, line):
        self.code.extend([" " * self.indent_level, line, "\n"])
    def add_section(self):
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section
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


class Templite:
    @staticmethod
    def split_tokens(text):
        return re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

    def __init__(self, text, *contexts):
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        code = CodeBuilder()
        code.add_line("def render_function(context):")
        code.indent()
        vars_code = code.add_section()
        code.add_line('globals().update(context)')
        code.add_line('class TrimLeft(str): pass')
        code.add_line('class TrimRight(str): pass')
        code.add_line('nil, false, true = None, False, True')
        code.add_line('class forloop: index = 1')
        code.add_line('''def finalize_result(result): return "\\n".join(result)''')
        code.add_line("result = []")
        code.add_line("")
        ops_stack = []

        tokens = self.split_tokens(text)
        
        i = 0;
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
                code.add_line("result.append(%s)" % ("str(%s)" % expr))

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
                    #self._variable(words[1], self.loop_vars)
                    code.add_line("for %s in %s:" % (words[1], self._expr_code(words[3]) ) )
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
                    frontmatter_include, template_include = self.context.get('includes', {})[words[1]]
                    tokens = tokens[:i + 1] + self.split_tokens(template_include) + tokens[i + 1:]
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    var_name = words[1]
                    code.add_line('%s = %s' % (var_name, expr))
                    #self._variable(var_name, self.all_vars)


                elif words[0] == 'seo':
                    code.add_line('#seo#')
        
                else:
                    self._syntax_error("Don't understand tag", words[0])

            else:
                if token:
                    code.add_line("result.append(%s)" % (repr(token)))
            
            if e == -3:
                code.add_line("result.append(TrimRight())")
            i += 1

        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("%s = context[%r]" % (var_name, var_name))

        code.add_line("return finalize_result(result)")
        code.dedent()
        
        print(str(code), file = sys.stderr)
        print(str(code), file = open('render.py', 'w'))

        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        expr = expr.strip()
        if expr.startswith('"') and expr.endswith('"'):
            return expr
        elif expr.startswith("'") and expr.endswith("'"):
            return expr
        elif "|" in expr:
            pipes = list(map(str.strip, expr.split("|")))
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                func_name, *func_args = func.split(':', maxsplit = 1)
                #self._variable(func_name, self.all_vars)
                if not func_args:
                    code = f"{func_name}({code})"
                    #code = f"context['{func_name}']({code})"
                    #code = "c_%s(%s)" % (func_name, code)
                else:
                    assert len(func_args) == 1
                    func_args = ', '.join(map(self._expr_code, func_args[0].split(',')))
                    code = f"{func_name}({code}, {func_args})"
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
        raise ValueError("%s: %r" % (msg, thing))

    def _variable(self, name, vars_set):
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)

    def render(self, context=None):
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context)

class NanoJekyllFilters:
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
        return html.escape(s)
    
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
        return [x[key] for x in xs]
    
    @staticmethod
    def append(xs, item):
        # https://shopify.github.io/liquid/filters/append/
        return xs.append(item) or xs

    @staticmethod
    def first(xs):
        # https://shopify.github.io/liquid/filters/first/
        return xs[0]

    @staticmethod
    def size(xs):
        # https://shopify.github.io/liquid/filters/size/
        return len(xs)

    @staticmethod
    def join(xs, sep):
        # https://shopify.github.io/liquid/filters/join/
        return sep.join(map(str, xs))


class NanoJekyll:
    def __init__(self, base_dir = '.', includes_dirname = '_includes', layouts_dirname = '_layouts', filters = {}, plugins = {}):
        self.filters = {}
        self.plugins = {}
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

    def render_layout(self, ctx = {}, layout = ''):
        filters = self.filters | NanoJekyllFilters.__dict__
        content = ''
        while layout:
            frontmatter, template = [l for k, l in self.layouts.items() if k == layout or os.path.splitext(k)[0] == layout][0] 
            content = Templite(template, filters, dict(includes = self.includes)).render(context = ctx | dict(content = content))
            layout = self.extract_layout_from_frontmatter(frontmatter)
        return content

attrdict = type('attrdict', (dict, ), dict(__getattr__ = dict.__getitem__, __setattr__ = dict.__setitem__)) 
jekylllist = type('jekylllist', (list, ), dict(size = property(list.__len__)))

if __name__ == '__main__':
    # https://jekyllrb.com/docs/rendering-process/
    jekyll = NanoJekyll()
    
    ctx = attrdict(
        content = 'fgh',

        paginator = attrdict(),

        page = attrdict(lang = 'asd', title = 'def', date = datetime.datetime(2024, 2, 12, 13, 27, 16, 182792), modified_date = None, author = None, url = ''), 
        site = attrdict(lang = 'klm', pages = [], header_pages = [], title = 'def', feed = attrdict(path = 'klm'), author = None, description = 'opq', minima = attrdict(social_links = [], date_format = "%b %-d, %Y"), disqus = attrdict(shortname = None), paginate = False, posts = jekylllist([]) ), 
        jekyll = attrdict(environment = attrdict()),
    )
    print(jekyll.render_layout(ctx = ctx, layout = 'page.html'))
    #print(jekyll.render_layout(ctx = ctx, layout = 'base.html'))
    #print(jekyll.render_layout(ctx = ctx, layout = 'post.html'))
    #print(jekyll.render_layout(ctx = ctx, layout = 'home.html'))
