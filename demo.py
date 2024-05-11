import datetime

import jekyll

j = jekyll.NanoJekyll()

ctx = dict(
    content = 'fgh',

    paginator = dict(),

    page = dict(lang = 'asd', title = 'def', date = datetime.datetime(2024, 2, 12, 13, 27, 16, 182792), modified_date = None, author = None, url = ''), 
    site = dict(lang = 'klm', pages = [], header_pages = [], title = 'def', feed = dict(path = 'klm'), author = None, description = 'opq', minima = dict(social_links = [], date_format = "%b %-d, %Y"), disqus = dict(shortname = None), paginate = False, posts = [] ), 
    jekyll = dict(environment = dict()),
)
print(j.render_layout(ctx = ctx, layout = 'page.html'))
#print(j.render_layout(ctx = ctx, layout = 'base.html'))
#print(j.render_layout(ctx = ctx, layout = 'post.html'))
#print(j.render_layout(ctx = ctx, layout = 'home.html'))
