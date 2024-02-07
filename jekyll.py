import os
import templite

class NanoJekyll:
    def __init__(self, base_dir, includes_dirname = '_includes', layouts_dirname = '_layouts'):
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
                
        

    def render_layout(self, ctx = {}, layout = ''):
        front_matter_layout, template_layout = self.layouts[layout]
        actual = templite.Templite(template_layout).render(context = dict(ctx, escape = lambda s: s))
        return actual


if __name__ == '__main__':
    jekyll = NanoJekyll(base_dir = '../../')
    print(jekyll.render_layout(ctx = dict(page = dict(title = 'asd'), content = 'fgh'), layout = 'page.html'))
