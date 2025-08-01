---
title: "<span id='nav-theme-icon'>🌚</span> <span id='nav-theme-text'>Toggle Dark Mode</span>"
nav_order: 0
layout: default
permalink: /theme-toggle/
---

<script>
// Immediately toggle theme when this page is accessed
document.addEventListener('DOMContentLoaded', function() {
  const body = document.body;
  const html = document.documentElement;
  const isDark = body.classList.contains('dark-mode');
  const newTheme = isDark ? 'light' : 'dark';
  
  // Apply theme
  if (newTheme === 'dark') {
    body.classList.add('dark-mode');
    html.classList.remove('light-mode');
  } else {
    body.classList.remove('dark-mode');
    html.classList.add('light-mode');
  }
  
  // Save preference
  localStorage.setItem('theme', newTheme);
  
  // Redirect back to previous page or home
  const referrer = document.referrer;
  if (referrer && referrer.includes(window.location.origin)) {
    window.location.href = referrer;
  } else {
    window.location.href = '/OpenCue/';
  }
});
</script>

# Theme Toggle

This page toggles between light and dark mode and redirects you back to where you came from.