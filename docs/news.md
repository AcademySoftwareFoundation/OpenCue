---
layout: default
title: <i class='fas fa-newspaper'></i>&nbsp;News
nav_order: 20
permalink: /news/
---

# News

Latest news, updates, and community announcements about OpenCue development and events.

{% assign news_posts = site.news | sort: "date" | reverse %}
{% for post in news_posts %}
- [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
