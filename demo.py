import os
import json
import markdown

import nanojekyll

global_variables = ['site', 'page', 'layout', 'theme', 'content', 'paginator', 'jekyll'] # https://jekyllrb.com/docs/variables/

output_dir = '_site'

layouts_dir = '_layouts'
includes_dir = '_includes'
icons_dir = '_includes/social-icons'

codegen_py = 'nanojekyllcodegen.py'

includes_basenames = ['footer.html', 'head.html', 'custom-head.html', 'social.html', 'social-item.html', 'svg_symbol.html', 'google-analytics.html',   'header.html', 'disqus_comments.html']

icons_basenames = ['devto.svg', 'flickr.svg', 'google_scholar.svg', 'linkedin.svg', 'pinterest.svg', 'telegram.svg', 'youtube.svg', 'dribbble.svg', 'github.svg', 'instagram.svg', 'mastodon.svg', 'rss.svg', 'twitter.svg', 'facebook.svg', 'gitlab.svg', 'keybase.svg', 'microdotblog.svg', 'stackoverflow.svg', 'x.svg']

layouts_basenames = ['base.html', 'page.html', 'post.html', 'home.html']

static_assets = {
    'assets/css/style.css' : 'assets/css/style.css'
}
dynamic_assets = {
    'assets/minima-social-icons.liquid' : 'assets/minima-social-icons.svg'
}

pages = {
    '404.html' : '404.html',
    'index.md' : 'index.html', 
    'about.md' : 'about.html'
}
posts = {
    '_posts/2016-05-19-super-short-article.md' : '2016-05-19-super-short-article.html', 
    '_posts/2016-05-20-super-long-article.md' : '2016-05-20-super-long-article.html', 
    '_posts/2016-05-20-welcome-to-jekyll.md' : '2016-05-20-welcome-to-jekyll.html', 
    '_posts/2016-05-20-my-example-post.md' : '2016-05-20-my-example-post.html', 
    '_posts/2016-05-20-this-post-demonstrates-post-content-styles.md' : '2016-05-20-this-post-demonstrates-post-content-styles.html'
}

context_path = 'context.json'

#####################################

ctx = json.load(open(context_path))

def read_template(path):
    frontmatter, content = nanojekyll.NanoJekyllTemplate.read_template(path)
    if path.endswith('.md'):
        content = markdown.markdown(content)
    return frontmatter, content

def render(cls, ctx = {}, content = '', template_name = '', templates = {}): # https://jekyllrb.com/docs/rendering-process/
    while template_name:
        frontmatter, template = [l for k, l in templates.items() if k == template_name or os.path.splitext(k)[0] == template_name][0] 
        content = cls(ctx | dict(content = content)).render(template_name)
        template_name = ([line.split(':')[1].strip() for line in frontmatter.splitlines() if line.strip().replace(' ', '').startswith('layout:')] or [None])[0]
    return content

#####################################

icons = {os.path.join(os.path.basename(icons_dir), basename) : open(os.path.join(icons_dir, basename)).read() for basename in icons_basenames} 

templates_layouts = {os.path.splitext(basename)[0] : read_template(os.path.join(layouts_dir, basename)) for basename in layouts_basenames} 
templates_includes = {basename: read_template(os.path.join(includes_dir, basename)) for basename in includes_basenames}
templates_pages = {input_path: read_template(input_path) for input_path in pages}
templates_posts = {input_path: read_template(input_path) for input_path in posts}
templates_assets = {input_path : read_template(input_path) for input_path in dynamic_assets}

templates_all = (templates_includes | templates_layouts | templates_pages | templates_posts | templates_assets)
cls, python_source = nanojekyll.NanoJekyllTemplate.codegen({k : v[1] for k, v in templates_all.items()}, includes = templates_includes | icons, global_variables = global_variables)

open(codegen_py, 'w').write(python_source)
print(codegen_py)

os.makedirs(output_dir, exist_ok = True)
print(output_dir)
for input_path, output_path in static_assets.items():
    output_path = os.path.join(output_dir, output_path or input_path)
    os.makedirs(os.path.dirname(output_path), exist_ok = True)
    with open(output_path, 'wb') as f, open(input_path, 'rb') as g:
        content = g.read()
        f.write(content)
    print(output_path)
for input_path, output_path in list(pages.items()) + list(dynamic_assets.items()) + list(posts.items()):
    output_path = os.path.join(output_dir, output_path or input_path)
    os.makedirs(os.path.dirname(output_path), exist_ok = True)
    with open(output_path, 'w') as f:
        f.write(render(cls, ctx, template_name = input_path, templates = templates_all))
    print(output_path)
