import json
import datetime

import jekyll

ctx = json.load(open('context.json'))

jek = jekyll.NanoJekyll(includes_dirname = '_includes', layouts_dirname = '_layouts')

print(jek.render_layout(ctx = ctx, layout = 'page.html'))
#print(jek.render_layout(ctx = ctx, layout = 'base.html'))
#print(jek.render_layout(ctx = ctx, layout = 'post.html'))
#print(jek.render_layout(ctx = ctx, layout = 'home.html'))
