# https://github.com/aosabook/500lines/tree/master/template-engine as a starting point

import re
import sys

class CodeBuilder(object):
    INDENT_STEP = 4      # PEP8 says so!
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


class Templite(object):
    @staticmethod
    def split_tokens(text):
        return re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

    #A simple template renderer, for a nano-subset of Django syntax.
    #Supported constructs are extended variable access::
    #    {{var.modifer.modifier|filter|filter}}
    #loops::
    #    {% for var in list %}...{% endfor %}
    #and ifs::
    #    {% if var %}...{% endif %}
    #Comments are within curly-hash markers::
    #    {# This will be ignored #}
    #Construct a Templite with the template text, then use `render` against a
    #dictionary context to create a finished string::
    #    templite = Templite('''
    #        <h1>Hello {{name|upper}}!</h1>
    #        {% for topic in topics %}
    #            <p>You are interested in {{topic}}.</p>
    #        {% endif %}
    #        ''',
    #        {'upper': str.upper},
    #    )
    #    text = templite.render({
    #        'name': "Ned",
    #        'topics': ['Python', 'Geometry', 'Juggling'],
    #    })
    def __init__(self, text, *contexts):
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        # We construct a function in source form, then compile it and hold onto
        # it, and execute it to render the template.
        code = CodeBuilder()
        code.add_line("def render_function(context, do_dots):")
        code.indent()
        vars_code = code.add_section()
        code.add_line("result = []")
        ops_stack = []

        # Split the text to form a list of tokens.
        tokens = self.split_tokens(text)
        
        i = 0;
        while i < len(tokens):
            token = tokens[i]
            if token.startswith('{#'): # comment
                i += 1
                continue

            elif token.startswith('{{'): # an expression to evaluate.
                expr = self._expr_code(token[2:-2].strip())
                code.add_line("result.append(%s)" % ("str(%s)" % expr))

            elif token.startswith('{%'):
                # Action tag: split into words and parse further.
                #flush_output()
                b = 3 if token.startswith('{%-') else 2
                e = -3 if token.endswith('-%}') else -2
                token_inner = token[b:e].strip()
                words = token_inner.split()
                #TODO: whitespace control not supported for now
                if words[0] == '-':
                    del words[0]
                if words[-1] == '-':
                    del words[-1]

                if words[0] == 'if':
                    # An if statement: evaluate the expression to determine if.
                    if len(words) != 2:
                        self._syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if %s:" % self._expr_code(words[1]))
                    code.indent()
                
                elif words[0] == 'for':
                    # A loop: iterate over expression result.
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line("for c_%s in %s:" % (words[1], self._expr_code(words[3]) ) )
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
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()

                elif words[0] == 'include':
                    #code.add_line('#include ' + words[-1])
                    frontmatter_include, template_include = self.context.get('includes', {})[words[1]]
                    tokens = tokens[:i + 1] + self.split_tokens(template_include) + tokens[i + 1:]
                
                elif words[0] == 'assign':
                    assert words[2] == '='
                    try:
                        expr = self._expr_code(token_inner.split('=', maxsplit = 1)[1].strip())
                    except:
                        breakpoint()
                    var_name = words[1]
                    code.add_line('%s = %s' % (var_name, expr))
                    self._variable(var_name, self.all_vars)


                elif words[0] == 'seo':
                    code.add_line('#seo#')
        
                else:
                    self._syntax_error("Don't understand tag", words[0])
            else:
                # Literal content.  If it isn't empty, output it.
                if token:
                    code.add_line("result.append(%s)" % (repr(token)))
                    #buffered.append(repr(token))
            i += 1

        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        
        print(str(code), file = sys.stderr)

        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        expr = expr.strip()
        #print('_expr_code:', expr)
        if expr.startswith('"') and expr.endswith('"'):
            return expr
        elif expr.startswith("'") and expr.endswith("'"):
            return expr
        elif "|" in expr:
            pipes = list(map(str.strip, expr.split("|")))
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                func_name, *func_args = func.split(':', maxsplit = 1)
                self._variable(func_name, self.all_vars)
                if not func_args:
                    code = "c_%s(%s)" % (func_name, code)
                else:
                    assert len(func_args) == 1
                    code = "c_%s(%s, %s)" % (func_name, code, self._expr_code(func_args[0]))
                    
        elif "." in expr:
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
            self._variable(expr, self.all_vars)
            code = "c_%s" % expr
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
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value
