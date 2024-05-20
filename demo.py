# TODO: read from _config.yml using https://gist.github.com/vadimkantorov/b26eda3645edb13feaa62b874a3e7f6f

import os
import json
import markdown

import nanojekyll

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

context = {
    "jekyll": {"environment": "production"},
    "paginator" : {
        "previous_page_path" : "/previous/page/path", 
        "next_page_path"     : "/next/page/path",
        "page"               : 2,
        "previous_page"      : 1,
        "next_page"          : 3 
    },

    "site" : {
        "title": "Your awesome title",
        "description": "Write an awesome description for your new site here. You can edit this line in _config.yml. It will appear in your document head meta (for Google search results) and in your feed.xml site description.",
        "author": {
            "name": "GitHub User",
            "email": "your-email@domain.com"
        },
        
        "minima" : {
            "date_format": "%b %-d, %Y",
            "social_links": [
                {"platform": "devto"           , "user_url": "https://dev.to/jekyll"},
                {"platform": "dribbble"        , "user_url": "https://dribbble.com/jekyll"},
                {"platform": "facebook"        , "user_url": "https://www.facebook.com/jekyll"},
                {"platform": "flickr"          , "user_url": "https://www.flickr.com/photos/jekyll"},
                {"platform": "github"          , "user_url": "https://github.com/jekyll/minima"},
                {"platform": "google_scholar"  , "user_url": "https://scholar.google.com/citations?user=qc6CJjYAAAAJ"},
                {"platform": "instagram"       , "user_url": "https://www.instagram.com/jekyll"},
                {"platform": "keybase"         , "user_url": "https://keybase.io/jekyll"},
                {"platform": "linkedin"        , "user_url": "https://www.linkedin.com/in/jekyll"},
                {"platform": "microdotblog"    , "user_url": "https://micro.blog/jekyll"},
                {"platform": "pinterest"       , "user_url": "https://www.pinterest.com/jekyll"},
                {"platform": "stackoverflow"   , "user_url": "https://stackoverflow.com/users/1234567/jekyll"},
                {"platform": "telegram"        , "user_url": "https://t.me/jekyll"},
                {"platform": "twitter"         , "user_url": "https://twitter.com/jekyllrb"},
                {"platform": "youtube"         , "user_url": "https://www.youtube.com/jekyll"},
                {"platform": "rss"             , "user_url": "https://jekyll.github.io/minima/feed.xml"},

                {"platform": "gitlab"          , "user_url": "https://gitlab.com/jekyll/minima"},
                {"platform": "mastodon"        , "user_url": "https://mastodon.social/jekyll"},
                {"platform": "x"               , "user_url": "https://x.com/jekyllrb"}
            ]
        },
        "show_excerpts": False,
        "baseurl": "/minimapython",

        "webmaster_verifications" : {
            "google": "googleverif",
            "bing" : "bingverif",
            "alexa": "alexaverif",
            "yandex": "yandexverif",
            "baidu": "baiduverif",
            "facebook": "facebookverif"
        },
        "facebook": {
            "admins": "admins",
            "publisher": "publisher",
            "app_id": "app_id"
        },
        "twitter": {
            "username": "username"
        },
        "feed": {"path": "feed.xml"},

        "header_pages": ["index.md", "about.md"],
    


        "time" : "now",
        "lang" : "en", 
        "show_drafts": False,
        "feed": {
            "excerpt_only": False
        },

        "paginate": True,

        "url": "https://vadimkantorov.github.io",
        "baseurl": "/nanojekyll",
        
        "author": {"name": "", "email": "", "uri": ""},
        
        "related_posts": [],
        "static_files": [],
        "html_pages": [],
        "html_files": [],
        "collections": [],
        "data": [],
        "documents": [],
        "categories": {},
        "tags": {},
        "pages" : [{"path": "about.md",  "title" : "title", "url": "url", "date": "date"}],
        "posts" : [{"path": "blogpost.md",  "title" : "title", "url": "url", "date": "date"}]
    },
    
    "page": {
        "layout": "default",
        "lang": "en",
        "title": "title",
        "list_title"   : "Archive",
        "description"  : "page description",
        "category"     : "category",
        "permalink"    : "permalink",
        "draft"        : False,
        "published"    : True,
        "content"      : "page content",
        "slug"          : "slug",
        "categories"    : ["asd", "def"],
        "tags"          : ["qwe", "rty"],
        "author"       : ["abc def", "ghi asd"],
        "collection"    : "collection",
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
    },

    "seo_tag": {
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
}


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
cls, python_source = nanojekyll.NanoJekyllTemplate.codegen({k : v[1] for k, v in templates_all.items()}, includes = templates_includes | icons, global_variables = global_variables, plugins = {'seo': nanojekyll.NanoJekyllPluginSeo, 'feed_meta' : nanojekyll.NanoJekyllPluginFeedMeta})
with open(codegen_py, 'w') as f:
    f.write(python_source)
print(codegen_py)
#cls = __import__('nanojekyllcodegen').NanoJekyllContext

assert cls
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
