---
layout: default
title: <i class='fas fa-rocket'></i>&nbsp;Releases
nav_order: 11
has_children: false
permalink: /releases/
---

# Releases

OpenCue release announcements and changelogs.

{% assign release_posts = site.pages | where: "parent", "Releases" | sort: "nav_order" %}
{% for post in release_posts %}
  {% unless post.url == page.url %}
- [{{ post.title | remove: '<i class="fas fa-rocket"></i>&nbsp;' }}]({{ post.url | relative_url }})
  {% endunless %}
{% endfor %}
