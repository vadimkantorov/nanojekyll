# https://github.com/jekyll/jekyll-seo-tag/blob/master/lib/template.html
# https://github.com/jekyll/jekyll-sitemap
# https://github.com/jekyll/jekyll-feed/blob/master/lib/jekyll-feed/generator.rb

minima_layout_base = '''
<!DOCTYPE html>
<html lang="{{ page.lang | default: site.lang | default: "en" }}">

    <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      
<!-- Begin Jekyll SEO tag v{{ seo_tag.version }} -->
{% if seo_tag.title? %}
  <title>{{ seo_tag.title }}</title>
{% endif %}

<meta name="generator" content="Jekyll v{{ jekyll.version }}" />

{% if seo_tag.page_title %}
  <meta property="og:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if seo_tag.author.name %}
  <meta name="author" content="{{ seo_tag.author.name }}" />
{% endif %}

<meta property="og:locale" content="{{ seo_tag.page_locale }}" />

{% if seo_tag.description %}
  <meta name="description" content="{{ seo_tag.description }}" />
  <meta property="og:description" content="{{ seo_tag.description }}" />
  <meta property="twitter:description" content="{{ seo_tag.description }}" />
{% endif %}

{% if site.url %}
  <link rel="canonical" href="{{ seo_tag.canonical_url }}" />
  <meta property="og:url" content="{{ seo_tag.canonical_url }}" />
{% endif %}

{% if seo_tag.site_title %}
  <meta property="og:site_name" content="{{ seo_tag.site_title }}" />
{% endif %}

{% if seo_tag.image %}
  <meta property="og:image" content="{{ seo_tag.image.path }}" />
  {% if seo_tag.image.height %}
    <meta property="og:image:height" content="{{ seo_tag.image.height }}" />
  {% endif %}
  {% if seo_tag.image.width %}
    <meta property="og:image:width" content="{{ seo_tag.image.width }}" />
  {% endif %}
  {% if seo_tag.image.alt %}
    <meta property="og:image:alt" content="{{ seo_tag.image.alt }}" />
  {% endif %}
{% endif %}

{% if page.date %}
  <meta property="og:type" content="article" />
  <meta property="article:published_time" content="{{ page.date | date_to_xmlschema }}" />
{% else %}
  <meta property="og:type" content="website" />
{% endif %}

{% if paginator.previous_page %}
  <link rel="prev" href="{{ paginator.previous_page_path | absolute_url }}" />
{% endif %}
{% if paginator.next_page %}
  <link rel="next" href="{{ paginator.next_page_path | absolute_url }}" />
{% endif %}

{% if seo_tag.image %}
  <meta name="twitter:card" content="{{ page.twitter.card | default: site.twitter.card | default: "summary_large_image" }}" />
  <meta property="twitter:image" content="{{ seo_tag.image.path }}" />
{% else %}
  <meta name="twitter:card" content="summary" />
{% endif %}

{% if seo_tag.image.alt %}
  <meta name="twitter:image:alt" content="{{ seo_tag.image.alt }}" />
{% endif %}

{% if seo_tag.page_title %}
  <meta property="twitter:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if site.twitter %}
  <meta name="twitter:site" content="@{{ site.twitter.username | remove:'@' }}" />

  {% if seo_tag.author.twitter %}
    <meta name="twitter:creator" content="@{{ seo_tag.author.twitter | remove:'@' }}" />
  {% endif %}
{% endif %}

{% if site.facebook %}
  {% if site.facebook.admins %}
    <meta property="fb:admins" content="{{ site.facebook.admins }}" />
  {% endif %}

  {% if site.facebook.publisher %}
    <meta property="article:publisher" content="{{ site.facebook.publisher }}" />
  {% endif %}

  {% if site.facebook.app_id %}
    <meta property="fb:app_id" content="{{ site.facebook.app_id }}" />
  {% endif %}
{% endif %}

{% if site.webmaster_verifications %}
  {% if site.webmaster_verifications.google %}
    <meta name="google-site-verification" content="{{ site.webmaster_verifications.google }}" />
  {% endif %}

  {% if site.webmaster_verifications.bing %}
    <meta name="msvalidate.01" content="{{ site.webmaster_verifications.bing }}" />
  {% endif %}

  {% if site.webmaster_verifications.alexa %}
    <meta name="alexaVerifyID" content="{{ site.webmaster_verifications.alexa }}" />
  {% endif %}

  {% if site.webmaster_verifications.yandex %}
    <meta name="yandex-verification" content="{{ site.webmaster_verifications.yandex }}" />
  {% endif %}

  {% if site.webmaster_verifications.baidu %}
    <meta name="baidu-site-verification" content="{{ site.webmaster_verifications.baidu }}" />
  {% endif %}

  {% if site.webmaster_verifications.facebook %}
    <meta name="facebook-domain-verification" content="{{ site.webmaster_verifications.facebook }}" />
  {% endif %}
{% elsif site.google_site_verification %}
  <meta name="google-site-verification" content="{{ site.google_site_verification }}" />
{% endif %}

<script type="application/ld+json">
  {{ seo_tag.json_ld | jsonify }}
</script>

<!-- End Jekyll SEO tag -->

      <link rel="stylesheet" href="{{ "/assets/css/style.css" | relative_url }}">
      {% comment %}<!-- {%- feed_meta -%} -->{% endcomment %}
      {%- if jekyll.environment == 'production' and site.google_analytics -%}
        <script async src="https://www.googletagmanager.com/gtag/js?id={{ site.google_analytics }}"></script>
        <script>
          window['ga-disable-{{ site.google_analytics }}'] = window.doNotTrack === "1" || navigator.doNotTrack === "1" || navigator.doNotTrack === "yes" || navigator.msDoNotTrack === "1";
          window.dataLayer = window.dataLayer || [];
          function gtag(){window.dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', '{{ site.google_analytics }}');
        </script>
      {%- endif -%}

      {%- include custom-head.html -%}
      
    </head>


  <body>

    <header class="site-header">

      <div class="wrapper">
        {%- assign default_paths = site.pages | map: "path" -%}
        {%- assign page_paths = site.header_pages | default: default_paths -%}
        {%- assign titles_size = site.pages | map: 'title' | join: '' | size -%}
        <a class="site-title" rel="author" href="{{ "/" | relative_url }}">{{ site.title | escape }}</a>

        {%- if titles_size > 0 -%}
          <nav class="site-nav">
            <input type="checkbox" id="nav-trigger" class="nav-trigger" />
            <label for="nav-trigger">
              <span class="menu-icon">
                <svg viewBox="0 0 18 15" width="18px" height="15px">
                  <path d="M18,1.484c0,0.82-0.665,1.484-1.484,1.484H1.484C0.665,2.969,0,2.304,0,1.484l0,0C0,0.665,0.665,0,1.484,0 h15.032C17.335,0,18,0.665,18,1.484L18,1.484z M18,7.516C18,8.335,17.335,9,16.516,9H1.484C0.665,9,0,8.335,0,7.516l0,0 c0-0.82,0.665-1.484,1.484-1.484h15.032C17.335,6.031,18,6.696,18,7.516L18,7.516z M18,13.516C18,14.335,17.335,15,16.516,15H1.484 C0.665,15,0,14.335,0,13.516l0,0c0-0.82,0.665-1.483,1.484-1.483h15.032C17.335,12.031,18,12.695,18,13.516L18,13.516z"/>
                </svg>
              </span>
            </label>

            <div class="trigger">
              {%- for path in page_paths -%}
                {%- assign my_page = site.pages | where: "path", path | first -%}
                {%- if my_page.title -%}
                <a class="page-link" href="{{ my_page.url | relative_url }}">{{ my_page.title | escape }}</a>
                {%- endif -%}
              {%- endfor -%}
            </div>
          </nav>
        {%- endif -%}
      </div>
    </header>

    <main class="page-content" aria-label="Content">
      <div class="wrapper">
        {{ content }}
      </div>
    </main>

    <footer class="site-footer h-card">
      <data class="u-url" href="{{ "/" | relative_url }}"></data>

      <div class="wrapper">

        <div class="footer-col-wrapper">
          <div class="footer-col">
            <p class="feed-subscribe">
              <a href="{{ site.feed.path | default: 'feed.xml' | absolute_url }}">
                <svg class="svg-icon orange">
                  <use xlink:href="{{ 'assets/minima-social-icons.svg#rss' | relative_url }}"></use>
                </svg><span>Subscribe</span>
              </a>
            </p>
          {%- if site.author %}
            <ul class="contact-list">
              {% if site.author.name -%}
                <li class="p-name">{{ site.author.name | escape }}</li>
              {% endif -%}
              {% if site.author.email -%}
                <li><a class="u-email" href="mailto:{{ site.author.email }}">{{ site.author.email }}</a></li>
              {%- endif %}
            </ul>
          {%- endif %}
          </div>
          <div class="footer-col">
            <p>{{ site.description | escape }}</p>
          </div>
        </div>

        <div class="social-links">
            <ul class="social-media-list">
            {%- for entry in site.minima.social_links -%}
                <li>{% assign entry = include.item %}
                  <a {% unless entry.platform == 'rss' %}rel="me" {% endunless %}href="{{ entry.user_url }}" target="_blank" title="{{ entry.title | default: entry.platform }}">
                    <svg class="svg-icon grey">
                      <use xlink:href="{{ '/assets/minima-social-icons.svg#' | append: entry.platform | relative_url }}"></use>
                    </svg>
                  </a>
                </li>
            {%- endfor -%}
            </ul>
        </div>

      </div>

    </footer>

  </body>

</html>
'''

minima_layout_page = '''
<article class="post">

  <header class="post-header">
    <h1 class="post-title">{{ page.title | escape }}</h1>
  </header>

  <div class="post-content">
    {{ content }}
  </div>

</article>
'''

minima_layout_post = '''
<article class="post h-entry" itemscope itemtype="http://schema.org/BlogPosting">

  <header class="post-header">
    <h1 class="post-title p-name" itemprop="name headline">{{ page.title | escape }}</h1>
    <p class="post-meta">
      {%- assign date_format = site.minima.date_format | default: "%b %-d, %Y" -%}
      <time class="dt-published" datetime="{{ page.date | date_to_xmlschema }}" itemprop="datePublished">
        {{ page.date | date: date_format }}
      </time>
      {%- if page.modified_date -%}
        ~ 
        {%- assign mdate = page.modified_date | date_to_xmlschema -%}
        <time class="dt-modified" datetime="{{ mdate }}" itemprop="dateModified">
          {{ mdate | date: date_format }}
        </time>
      {%- endif -%}
      {%- if page.author -%}
        • {% for author in page.author %}
          <span itemprop="author" itemscope itemtype="http://schema.org/Person">
            <span class="p-author h-card" itemprop="name">{{ author }}</span></span>
            {%- if forloop.last == false %}, {% endif -%}
        {% endfor %}
      {%- endif -%}</p>
  </header>

  <div class="post-content e-content" itemprop="articleBody">
    {{ content }}
  </div>

  {%- if site.disqus.shortname -%}
    {%- include disqus_comments.html -%}
  {%- endif -%}

  <a class="u-url" href="{{ page.url | relative_url }}" hidden></a>
</article>

'''


######
