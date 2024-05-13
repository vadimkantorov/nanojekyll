import os
import json

import nanojekyll

output_dir = '_site'

layouts_dir = '_layouts'
includes_dir = '_includes'
icons_dir = '_includes/social-icons'

includes_basenames = ['custom-head.html', 'footer.html', 'head.html', 'social.html', 'disqus_comments.html',  'google-analytics.html',  'header.html',  'social-item.html',  'svg_symbol.html']

icons_basenames = ['devto.svg', 'flickr.svg', 'google_scholar.svg', 'linkedin.svg', 'pinterest.svg', 'telegram.svg', 'youtube.svg', 'dribbble.svg', 'github.svg', 'instagram.svg', 'mastodon.svg', 'rss.svg', 'twitter.svg', 'facebook.svg', 'gitlab.svg', 'keybase.svg', 'microdotblog.svg', 'stackoverflow.svg', 'x.svg']

layouts_basenames = ['base.html', 'page.html', 'post.html', 'home.html']

static_assets = {
    'assets/css/style.css' : None
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

ctx = json.load(open('context.json'))

jek = nanojekyll.NanoJekyll(includes = includes | icons, layouts = layouts) 
layouts = {os.path.splitext(basename)[0] : nanojekyll.NanoJekyll.read_template(os.path.join(layouts_dir, basename)) for basename in layouts_basenames} 
icons = {os.path.join(os.path.basename(icons_dir), basename) : open(os.path.join(icons_dir, basename)).read() for basename in icons_basenames} 
includes = {basename: nanojekyll.NanoJekyll.read_template(os.path.join(includes_dir, basename)) for basename in includes_basenames}
includes |= {os.path.splitext(k)[0] : v for k, v in includes.items()}

os.makedirs(output_dir, exist_ok = True)
print(output_dir)
for input_path, output_path in static_assets.items():
    output_path = os.path.join(output_dir, output_path or input_path)
    os.makedirs(os.path.dirname(output_path), exist_ok = True)
    with open(output_path, 'wb') as f, open(input_path, 'rb') as g:
        content = g.read()
        f.write(content)
    print(output_path)
for input_path, output_path in list(dynamic_assets.items()) + list(pages.items()) + list(posts.items()):
    output_path = os.path.join(output_dir, output_path or input_path)
    os.makedirs(os.path.dirname(output_path), exist_ok = True)
    with open(output_path, 'w') as f:
        frontmatter, template = jek.read_template(input_path)
        layout = jek.extract_layout_from_frontmatter(frontmatter)
        f.write(jek.render(ctx = ctx, template = template, layout = layout))
    print(output_path)
