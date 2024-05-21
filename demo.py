import os
import json
import markdown

import nanojekyll

config_yml = '_config.yml'

global_variables = ['site', 'page', 'layout', 'theme', 'content', 'paginator', 'jekyll', 'seo_tag'] # https://jekyllrb.com/docs/variables/

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

config = nanojekyll.yaml_loads(open(config_yml).read())

ctx = dict(site = config, jekyll = dict(environment = "production"), paginator = {})

ctx["site"].update(dict(
    feed = dict(path = "feed.xml", excerpt_only = False),

    time = "now",
    lang = "en", 
    show_drafts = False,

    url = "https://vadimkantorov.github.io",
    baseurl = "/nanojekyll",
    
    collections = [],
    categories = {},
    tags = {},

    pages = [{"path": "about.md", "title" : "title", "url": "url", "date": "date"}],
    posts = [{"path": "blogpost.md", "title" : "title", "url": "url", "date": "date"}],
    header_pages = ["index.md", "about.md"]
))

#cts['site']['paginate'], ctx['paginator'] = True, dict(previous_page_path = '/.../', next_page_path = '/.../', page = 2, previous_page = 1, next_page = 3, posts = ctx['site']['posts'])


def read_template(path):
    frontmatter, content = nanojekyll.NanoJekyllTemplate.read_template(path)
    if path.endswith('.md'):
        content = markdown.markdown(content)
    return frontmatter, content

def render(cls, ctx = {}, content = '', template_name = '', templates = {}):
    # https://jekyllrb.com/docs/rendering-process/
    while template_name:
        frontmatter, template = [l for k,l in templates.items() if k == template_name or os.path.splitext(k)[0] == template_name][0] 
        content = cls(ctx | dict(content = content)).render(template_name)
        template_name = frontmatter.get('layout')
    return content

#####################################

icons = {os.path.join(os.path.basename(icons_dir), basename) : open(os.path.join(icons_dir, basename)).read() for basename in icons_basenames} 

templates_layouts = {os.path.splitext(basename)[0] : read_template(os.path.join(layouts_dir, basename)) for basename in layouts_basenames} 
templates_includes = {basename: read_template(os.path.join(includes_dir, basename)) for basename in includes_basenames}
templates_pages = {input_path: read_template(input_path) for input_path in pages}
templates_posts = {input_path: read_template(input_path) for input_path in posts}
templates_assets = {input_path : read_template(input_path) for input_path in dynamic_assets}

templates_all = (templates_includes | templates_layouts | templates_pages | templates_posts | templates_assets)
cls, python_source = nanojekyll.NanoJekyllTemplate.codegen({k : v[1] for k, v in templates_all.items()}, includes = templates_includes | icons, global_variables = global_variables, plugins = {'seo': nanojekyll.NanoJekyllPluginSeo, 'feed_meta' : nanojekyll.NanoJekyllPluginFeedMeta, 'feed_meta_xml' : nanojekyll.NanoJekyllPluginFeedMetaXml})
with open(codegen_py, 'w') as f:
    f.write(python_source)
#cls = __import__('nanojekyllcodegen').NanoJekyllContext
print(codegen_py)

assert cls

if output_path := ctx['site'].get('feed', {}).get('path', ''):
    # set up page
    output_path = os.path.join(output_dir, output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok = True)
    with open(output_path, 'w') as f:
        content = cls(ctx).render('feed_meta_xml', is_plugin = True)
        f.write(content)
    print(output_path)

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
        ctx['page'] = {
            "layout": "default",
            "lang": "en",
            "title": "title",
            "list_title"   : "Archive",
            "description"  : "page description",
            #"category"     : "category",
            "permalink"    : "permalink",
            "draft"        : False,
            "published"    : True,
            "content"      : "page content",
            "slug"          : "slug",
            "categories"    : ["asd", "def"],
            #"tags"          : ["qwe", "rty"],
            "author"       : ["abc def", "ghi asd"],
            "collection"    : "posts",
            "date"          : "date",
            "modified_date" : "modified date",
            "path"          : "path",
            "dir"           : "dir",
            
            "excerpt"       : "excerpt",
            "url"           : "url", 
            "id"            : "path",

            "twitter"       : {"card":  "summary_large_image"},
            "image"         : {"path" : "path", "height" : "0", "width" : "0", "alt" : ""},

            "previous"      : None,
            "next"          : None,
            "type"          : "page"
        }


        ctx["seo_tag"] = {
            "canonical_url" : "/canonical/url/",
            "page_locale" : "en_US",
            "description" : "description",
            "site_title" : "site title", 
            "page_title" : "page title",
            "title" : "page title",
            "author" : {"name": "name"},
        
            "image" : {}, 
            "json_ld": {
                "@context" : "https://schema.org",
                "@type" : "WebPage",
                "description" : "description", 
                "url": "canonical url", 
                "headline" : "page title", 
                "name": "site title", 
                "author" : {"@type" : "Person", "name": "name", "url" : "url"} 
            }
        }
        
        f.write(render(cls, ctx, template_name = input_path, templates = templates_all))
    print(output_path)
