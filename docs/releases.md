---
layout: default
title: <i class='fas fa-rocket'></i>&nbsp;Releases
nav_order: 30
permalink: /releases/
---

# Releases

OpenCue release announcements and changelogs.

{% assign release_posts = site.releases | sort: "date" | reverse %}
{% for post in release_posts %}
- [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
