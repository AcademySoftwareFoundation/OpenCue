---
layout: default
title: <i class='fas fa-newspaper'></i>&nbsp;News
nav_order: 10
has_children: false
permalink: /news/
---

# News

Latest news, updates, and community announcements about OpenCue development and events.

{% assign news_posts = site.pages | where: "parent", "News" | sort: "nav_order" %}
{% for post in news_posts %}
  {% unless post.url == page.url %}
- [{{ post.title | remove: '<i class="fas fa-newspaper"></i>&nbsp;' }}]({{ post.url | relative_url }})
  {% endunless %}
{% endfor %}
